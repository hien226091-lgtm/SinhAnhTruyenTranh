"""Post-processing utilities for comic panel outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Tuple

from PIL import Image, ImageDraw, ImageOps


ASPECT_RATIO_DIMENSIONS = {
    "aspect_ratio_1_1": (1, 1),
    "aspect_ratio_16_9": (16, 9),
    "aspect_ratio_9_16": (9, 16),
}


DEFAULT_FRAME_PADDING = 0
DEFAULT_FRAME_BORDER = 6


def _target_ratio(aspect_ratio_key: str) -> float:
    """Get numeric ratio from aspect ratio key."""
    width, height = ASPECT_RATIO_DIMENSIONS.get(aspect_ratio_key, (16, 9))
    return width / height


def enforce_aspect_ratio(image_path: str | Path, aspect_ratio_key: str) -> None:
    """Fit image to exact target ratio with padding (no content crop)."""
    path = Path(image_path)
    if not path.exists():
        return

    target = _target_ratio(aspect_ratio_key)

    with Image.open(path) as img:
        img = img.convert("RGB")
        width, height = img.size
        if width <= 0 or height <= 0:
            return

        current = width / height
        if abs(current - target) < 0.002:
            img.save(path, quality=95)
            return

        if current > target:
            target_width = width
            target_height = max(1, int(round(width / target)))
        else:
            target_height = height
            target_width = max(1, int(round(height * target)))

        canvas = Image.new("RGB", (target_width, target_height), color=(255, 255, 255))
        x = (target_width - width) // 2
        y = (target_height - height) // 2
        canvas.paste(img, (x, y))
        canvas.save(path, quality=95)


def apply_comic_frame(
    image_path: str | Path,
    padding: int = DEFAULT_FRAME_PADDING,
    border: int = DEFAULT_FRAME_BORDER,
) -> None:
    """Apply a black frame directly on the original image (no white canvas expand)."""
    path = Path(image_path)
    if not path.exists():
        return

    with Image.open(path) as img:
        img = img.convert("RGB")
        framed = img.copy()
        draw = ImageDraw.Draw(framed)

        inset = max(0, padding) + max(1, border // 2)
        x0 = inset
        y0 = inset
        x1 = framed.width - inset - 1
        y1 = framed.height - inset - 1

        if x1 <= x0 or y1 <= y0:
            framed.save(path, quality=95)
            return

        draw.rectangle((x0, y0, x1, y1), outline="black", width=max(1, border))
        framed.save(path, quality=95)


def split_into_episodes(items: List[str], max_frames_per_episode: int = 6) -> List[List[str]]:
    """Split frame list into episodes with at most max_frames_per_episode items."""
    if max_frames_per_episode <= 0:
        max_frames_per_episode = 6

    result: List[List[str]] = []
    for index in range(0, len(items), max_frames_per_episode):
        result.append(items[index : index + max_frames_per_episode])
    return result


def compose_episode_page(
    image_paths: Iterable[str],
    output_page_path: str | Path,
    columns: int = 2,
    panel_border: int = 4,
    gap: int = 6,
    margin: int = 8,
) -> None:
    """Compose up to 6 panels into one comic page with black panel borders."""
    paths = [Path(item) for item in image_paths]
    paths = [path for path in paths if path.exists()]
    if not paths:
        raise ValueError("No image files to compose")

    images: List[Image.Image] = []
    try:
        for path in paths:
            images.append(Image.open(path).convert("RGB"))

        widths = [img.width for img in images]
        heights = [img.height for img in images]
        cell_w = max(widths)
        cell_h = max(heights)

        rows = (len(images) + columns - 1) // columns
        canvas_w = margin * 2 + columns * (cell_w + panel_border * 2) + (columns - 1) * gap
        canvas_h = margin * 2 + rows * (cell_h + panel_border * 2) + (rows - 1) * gap
        canvas = Image.new("RGB", (canvas_w, canvas_h), color=(255, 255, 255))

        for idx, img in enumerate(images):
            row = idx // columns
            col = idx % columns
            x = margin + col * (cell_w + panel_border * 2 + gap)
            y = margin + row * (cell_h + panel_border * 2 + gap)

            panel = ImageOps.contain(img, (cell_w, cell_h), method=Image.Resampling.LANCZOS)
            panel_canvas = Image.new("RGB", (cell_w, cell_h), color=(255, 255, 255))
            px = (cell_w - panel.width) // 2
            py = (cell_h - panel.height) // 2
            panel_canvas.paste(panel, (px, py))
            panel = ImageOps.expand(panel_canvas, border=panel_border, fill="black")
            canvas.paste(panel, (x, y))

        output_path = Path(output_page_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path, quality=95)
    finally:
        for img in images:
            img.close()


def export_pdf_from_images(image_paths: Iterable[str], output_pdf_path: str | Path) -> None:
    """Export a list of images into a multi-page PDF."""
    paths = [Path(item) for item in image_paths]
    paths = [path for path in paths if path.exists()]
    if not paths:
        raise ValueError("No image files to export")

    images: List[Image.Image] = []
    try:
        for path in paths:
            images.append(Image.open(path).convert("RGB"))

        first = images[0]
        rest = images[1:]
        output_path = Path(output_pdf_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        first.save(output_path, save_all=True, append_images=rest)
    finally:
        for img in images:
            img.close()


def write_image_manifest(manifest_path: str | Path, entries: Iterable[dict]) -> None:
    """Write a JSON manifest describing generated images and their aspect ratios."""
    path = Path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"images": list(entries)}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
