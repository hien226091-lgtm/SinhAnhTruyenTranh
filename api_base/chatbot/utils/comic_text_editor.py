"""Compatibility shim for legacy subtitle APIs.

This module intentionally does not perform any local OCR/text overlay or bubble
analysis. Dialogue rendering is delegated entirely to Gemini image generation.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List


def _copy_if_needed(src: str, dst: str) -> None:
    """Copy source image to destination when paths differ."""
    src_path = Path(src)
    dst_path = Path(dst)
    if src_path.resolve() == dst_path.resolve():
        return
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src_path, dst_path)


class AITextBubbleAgent:
    """No-op agent kept for backward compatibility."""

    def render(
        self,
        path_anh_goc: str,
        path_anh_xuat: str,
        danh_sach_text: List[str],
        sfx: str = "",
    ) -> dict:
        _copy_if_needed(path_anh_goc, path_anh_xuat)
        return {
            "bubble_count": 0,
            "placed_dialogue_count": 0,
            "mode": "gemini-image-only",
            "note": "Local subtitle rendering is disabled.",
        }


AI_BUBBLE_TEXT_AGENT = AITextBubbleAgent()


def ai_vietsub(
    path_anh_goc: str,
    path_anh_xuat: str,
    danh_sach_text: List[str],
    sfx: str = "",
) -> dict:
    """Legacy API. Keep passthrough behavior only."""
    try:
        return AI_BUBBLE_TEXT_AGENT.render(path_anh_goc, path_anh_xuat, danh_sach_text, sfx)
    except Exception as exc:
        print(f"Warning: subtitle shim fallback copy failed: {exc}")
        _copy_if_needed(path_anh_goc, path_anh_xuat)
        return {
            "bubble_count": 0,
            "placed_dialogue_count": 0,
            "mode": "gemini-image-only",
            "note": "Fallback copy used.",
        }


def auto_vietsub(
    path_anh_goc: str,
    path_anh_xuat: str,
    danh_sach_text: List[str],
    sfx: str = "",
) -> None:
    """Backward-compatible wrapper around ai_vietsub."""
    ai_vietsub(path_anh_goc, path_anh_xuat, danh_sach_text, sfx)
