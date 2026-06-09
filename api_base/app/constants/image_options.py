"""Canonical Gemini image options and normalization helpers."""

from __future__ import annotations

from typing import Dict, List


GEMINI_ASPECT_RATIOS: List[str] = [
    "1:1",
    "1:4",
    "1:8",
    "2:3",
    "3:2",
    "3:4",
    "4:1",
    "4:3",
    "4:5",
    "5:4",
    "8:1",
    "9:16",
    "16:9",
    "21:9",
]

GEMINI_IMAGE_SIZES: List[str] = ["512", "1K", "2K", "4K"]

DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_IMAGE_SIZE = "2K"

# Backward compatibility with legacy layout keys used in earlier project versions.
LEGACY_ASPECT_RATIO_ALIASES: Dict[str, str] = {
    "aspect_ratio_1_1": "1:1",
    "aspect_ratio_16_9": "16:9",
    "aspect_ratio_9_16": "9:16",
    "aspect_ratio_1_4": "1:4",
    "aspect_ratio_1_8": "1:8",
    "aspect_ratio_2_3": "2:3",
    "aspect_ratio_3_2": "3:2",
    "aspect_ratio_3_4": "3:4",
    "aspect_ratio_4_1": "4:1",
    "aspect_ratio_4_3": "4:3",
    "aspect_ratio_4_5": "4:5",
    "aspect_ratio_5_4": "5:4",
    "aspect_ratio_8_1": "8:1",
    "aspect_ratio_21_9": "21:9",
}


def normalize_aspect_ratio(value: str | None) -> str:
    """Normalize aspect ratio input to canonical Gemini format (e.g. 16:9)."""
    if value is None:
        return DEFAULT_ASPECT_RATIO

    normalized = str(value).strip()
    if not normalized:
        return DEFAULT_ASPECT_RATIO

    if normalized in GEMINI_ASPECT_RATIOS:
        return normalized

    alias = LEGACY_ASPECT_RATIO_ALIASES.get(normalized)
    if alias:
        return alias

    if normalized.startswith("aspect_ratio_"):
        ratio_candidate = normalized.removeprefix("aspect_ratio_").replace("_", ":")
        if ratio_candidate in GEMINI_ASPECT_RATIOS:
            return ratio_candidate

    return DEFAULT_ASPECT_RATIO


def normalize_image_size(value: str | None) -> str:
    """Normalize image size input to canonical Gemini format (512, 1K, 2K, 4K)."""
    if value is None:
        return DEFAULT_IMAGE_SIZE

    normalized = str(value).strip().upper()
    if not normalized:
        return DEFAULT_IMAGE_SIZE

    if normalized in GEMINI_IMAGE_SIZES:
        return normalized

    if normalized.endswith("K") and normalized[:-1].isdigit():
        candidate = f"{int(normalized[:-1])}K"
        if candidate in GEMINI_IMAGE_SIZES:
            return candidate

    if normalized.isdigit() and normalized in GEMINI_IMAGE_SIZES:
        return normalized

    return DEFAULT_IMAGE_SIZE


def aspect_ratio_to_legacy_key(value: str | None) -> str:
    """Convert canonical aspect ratio to legacy key style for backward compatibility."""
    ratio = normalize_aspect_ratio(value)
    return f"aspect_ratio_{ratio.replace(':', '_')}"
