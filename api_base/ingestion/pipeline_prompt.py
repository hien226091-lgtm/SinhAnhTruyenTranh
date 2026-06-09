"""CLI pipeline to generate one image from prompt + aspect ratio + output path."""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

# Allow running this file directly from repository root with `python .../pipeline_prompt.py`.
API_BASE_DIR = Path(__file__).resolve().parents[1]
if str(API_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(API_BASE_DIR))

from api_base.app.config import CONFIG
from api_base.app.constants.image_options import (
    DEFAULT_ASPECT_RATIO,
    DEFAULT_IMAGE_SIZE,
    normalize_aspect_ratio,
    normalize_image_size,
)
from api_base.chatbot.services.ai_generator import get_last_image_error, tao_anh_truyen_tranh


def _resolve_output_path(raw_output: str) -> Path:
    """Resolve output target path from user input."""
    output_path = Path(raw_output).expanduser()
    if not output_path.is_absolute():
        output_path = (Path.cwd() / output_path).resolve()

    # If user provides a directory-like path, use a default filename.
    if output_path.suffix == "":
        output_path = output_path / "Anh_pipeline_cli.jpg"

    return output_path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for one-shot image generation."""
    parser = argparse.ArgumentParser(description="Generate one image from prompt + aspect ratio + output path")
    parser.add_argument("--mo-ta", required=True, help="Mo ta hinh anh can sinh")
    parser.add_argument(
        "--aspect-ratio",
        default=DEFAULT_ASPECT_RATIO,
        help="Ti le anh (vi du: 16:9, 1:1, 9:16, 21:9)",
    )
    parser.add_argument(
        "--image-size",
        default=DEFAULT_IMAGE_SIZE,
        help="Do phan giai anh: 512, 1K, 2K, 4K",
    )
    parser.add_argument("--output", required=True, help="Duong dan file anh dau ra")
    parser.add_argument("--character-description", default="", help="Mo ta nhan vat bo sung (tuy chon)")
    parser.add_argument("--session-id", default="default", help="Session id de tai anh tham chieu (tuy chon)")
    parser.add_argument("--thoai-trai", default="...", help="Thoai bong ben trai (tuy chon)")
    parser.add_argument("--thoai-phai", default="...", help="Thoai bong ben phai (tuy chon)")
    parser.add_argument("--sfx", default="", help="SFX text (tuy chon)")
    parser.add_argument("--overwrite", action="store_true", help="Ghi de file dau ra neu da ton tai")
    return parser.parse_args()


def main() -> int:
    """Execute one-shot generation pipeline."""
    args = parse_args()

    output_path = _resolve_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not args.overwrite:
        print(f"Loi: File dau ra da ton tai: {output_path}")
        print("Them --overwrite neu muon ghi de.")
        return 1

    aspect_ratio = normalize_aspect_ratio(args.aspect_ratio)
    image_size = normalize_image_size(args.image_size)

    configured_output_dir = CONFIG.outputs_dir.resolve()
    is_target_in_config_dir = output_path.parent.resolve() == configured_output_dir

    if is_target_in_config_dir:
        temp_filename = output_path.name
    else:
        temp_filename = f"pipeline_tmp_{int(time.time() * 1000)}_{output_path.name}"

    print("Dang sinh anh voi Gemini...")
    print(f"- Mo ta: {args.mo_ta}")
    print(f"- Ti le: {aspect_ratio}")
    print(f"- Do phan giai: {image_size}")
    print(f"- Dau ra: {output_path}")

    generated = tao_anh_truyen_tranh(
        kich_ban=args.mo_ta,
        ten_file_dau_ra=temp_filename,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        character_description=args.character_description,
        session_id=args.session_id,
        thoai_trai=args.thoai_trai,
        thoai_phai=args.thoai_phai,
        sfx=args.sfx,
    )

    if not generated:
        detail = get_last_image_error() or "Khong ro nguyen nhan"
        print(f"Loi: Tao anh that bai. Chi tiet: {detail}")
        return 1

    generated_path = Path(generated).resolve()

    # If target is outside configured output dir, copy result to user-specified path.
    if generated_path != output_path.resolve():
        shutil.copyfile(generated_path, output_path)
        if not is_target_in_config_dir:
            generated_path.unlink(missing_ok=True)

    print(f"Hoan tat: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
