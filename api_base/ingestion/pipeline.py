"""Pipeline for generating comic pages from layout and script data."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

# Allow running this file directly from repository root with `python .../pipeline.py`.
API_BASE_DIR = Path(__file__).resolve().parents[1]
if str(API_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(API_BASE_DIR))

from api_base.app.config import CONFIG
from api_base.app.constants.image_options import DEFAULT_ASPECT_RATIO, DEFAULT_IMAGE_SIZE, aspect_ratio_to_legacy_key, normalize_aspect_ratio, normalize_image_size
from api_base.app.utils.comic_postprocess import write_image_manifest
from api_base.chatbot.services.ai_generator import tao_anh_truyen_tranh


@dataclass
class PipelineConfig:
    """Configuration for pipeline layout and rate limiting."""

    margin: int = 8
    gap: int = 6
    panel_border: int = 4
    rate_limit_delay: int = 5
    frames_per_episode: int = 6


def setup_logger(log_file: str = "pipeline.log") -> logging.Logger:
    """Configure a logger for pipeline operations."""
    logger = logging.getLogger("Pipeline")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


logger = setup_logger(str(CONFIG.base_dir / "pipeline.log"))


def doc_file_json(duong_dan: str) -> Optional[List[Dict]]:
    """Safely read a JSON file."""
    try:
        file_path = Path(duong_dan)

        if not file_path.exists():
            logger.error(f"File khong ton tai: {duong_dan}")
            return None

        if not file_path.is_file():
            logger.error(f"Duong dan khong phai file: {duong_dan}")
            return None

        with open(duong_dan, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"Doc thanh cong: {duong_dan} ({len(data)} muc)")
        return data

    except json.JSONDecodeError as exc:
        logger.error(f"File JSON khong hop le {duong_dan}: {exc}")
        return None
    except Exception as exc:
        logger.error(f"Loi khi doc file {duong_dan}: {exc}")
        return None


def xuat_khung_hinh(
    index: int,
    layout_item: Dict,
    script_item: Dict,
    output_dir: str,
    config: PipelineConfig,
) -> Optional[str]:
    """Render a single panel image (with smart resume)."""
    khung_so = layout_item.get("khung_so", index + 1)
    ty_le = normalize_aspect_ratio(layout_item.get("aspect_ratio", DEFAULT_ASPECT_RATIO))
    image_size = normalize_image_size(layout_item.get("image_size", DEFAULT_IMAGE_SIZE))

    mo_ta = script_item.get("mo_ta_hinh_anh", "")
    thoai_trai = script_item.get("thoai_trai", "...")
    thoai_phai = script_item.get("thoai_phai", "...")
    sfx = script_item.get("sfx", "")

    if not mo_ta or mo_ta.strip() == "":
        logger.warning(f"Khung {khung_so}: Mo ta anh trong, bo qua")
        return None

    path_final = os.path.join(output_dir, f"Anh_{khung_so}.jpg")

    if os.path.exists(path_final):
        logger.info(f"Khung {khung_so} da ton tai ({path_final}), bo qua tao moi.")
        return path_final

    logger.info(f"Bat dau ve Khung {khung_so}: {ty_le} @ {image_size}")

    try:
        anh_ve_xong = tao_anh_truyen_tranh(
            mo_ta,
            f"Anh_{khung_so}.jpg",
            ty_le,
            image_size=image_size,
            thoai_trai=thoai_trai,
            thoai_phai=thoai_phai,
            sfx=sfx,
        )

        if not anh_ve_xong:
            logger.error("Tao anh AI that bai")
            return None

        if not os.path.exists(path_final):
            logger.error("Xuat anh that bai")
            return None

        logger.info(f"Khung {khung_so} hoan tat")
        return path_final

    except Exception as exc:
        logger.error(f"Loi xu ly khung {khung_so}: {exc}")
        return None


def xu_ly_pipeline(
    data_layout: List[Dict],
    data_script: List[Dict],
    output_dir: str,
    config: PipelineConfig,
) -> list[dict]:
    """Process the full pipeline to generate panel images."""
    danh_sach_file_hoan_thanh: list[dict] = []
    so_luong_khung = min(len(data_layout), len(data_script))

    logger.info(f"Bat dau xu ly {so_luong_khung} khung hinh")

    for i in range(so_luong_khung):
        path_final = xuat_khung_hinh(i, data_layout[i], data_script[i], output_dir, config)

        if path_final:
            ty_le = normalize_aspect_ratio(data_layout[i].get("aspect_ratio", DEFAULT_ASPECT_RATIO))
            danh_sach_file_hoan_thanh.append(
                {
                    "filename": Path(path_final).name,
                    "url": f"/outputs/{Path(path_final).name}",
                    "aspect_ratio_key": aspect_ratio_to_legacy_key(ty_le),
                    "aspect_ratio_label": ty_le,
                }
            )

        if path_final and os.path.exists(path_final):
            if i < so_luong_khung - 1:
                logger.debug(f"Cho {config.rate_limit_delay}s de tranh Rate Limit...")
                time.sleep(config.rate_limit_delay)

    return danh_sach_file_hoan_thanh


def main() -> int:
    """Run pipeline from CLI."""
    parser = argparse.ArgumentParser(description="He thong tich hop sinh truyen tranh AI")
    parser.add_argument("--layout", type=str, required=True, help="Duong dan den file layout.json")
    parser.add_argument("--script", type=str, required=True, help="Duong dan den file script.json")
    parser.add_argument(
        "--output",
        type=str,
        default=str(CONFIG.outputs_dir),
        help="Thu muc output",
    )

    args = parser.parse_args()

    logger.info("Pipeline bat dau")
    start_time = time.time()

    data_layout = doc_file_json(args.layout)
    data_script = doc_file_json(args.script)

    if not data_layout or not data_script:
        logger.critical("Khong doc duoc file input, dung he thong.")
        return 1

    output_dir = args.output
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    config = PipelineConfig()

    notes = xu_ly_pipeline(data_layout, data_script, output_dir, config)

    if notes:
        manifest_path = Path(output_dir) / "anh_manifest.json"
        write_image_manifest(manifest_path, notes)
    else:
        logger.warning("Khong co khung hinh nao xu ly thanh cong, bo qua luu anh")
        return 1

    elapsed = time.time() - start_time
    logger.info(f"Tong thoi gian: {elapsed:.1f}s ({elapsed / 60:.1f} phut)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
