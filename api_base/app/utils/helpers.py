"""Shared helper utilities used across the application."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
import re


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]")


def ensure_dir(path: Path) -> Path:
    """Create the directory if it does not exist and return the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(filename: str) -> str:
    """Return a filesystem-safe filename with unsafe characters replaced."""
    safe = _SAFE_NAME_RE.sub("_", filename).strip("._")
    return safe or "file"


def resolve_under(base_dir: Path, *parts: str) -> Path:
    """Resolve a path under base_dir and prevent path traversal."""
    candidate = (base_dir / Path(*parts)).resolve()
    base_dir = base_dir.resolve()
    if base_dir not in candidate.parents and candidate != base_dir:
        raise ValueError("Invalid path traversal attempt")
    return candidate


def list_files(directory: Path, extensions: Iterable[str] | None = None) -> list[Path]:
    """List files in a directory with optional extension filtering."""
    if not directory.exists():
        return []
    files = [item for item in directory.iterdir() if item.is_file()]
    if not extensions:
        return files
    normalized = {ext.lower() for ext in extensions}
    return [item for item in files if item.suffix.lower() in normalized]
