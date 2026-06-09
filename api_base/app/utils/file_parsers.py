"""Utilities for parsing uploaded script/layout files."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

from api_base.app.constants.image_options import DEFAULT_ASPECT_RATIO, DEFAULT_IMAGE_SIZE, normalize_aspect_ratio, normalize_image_size


SUPPORTED_SCRIPT_EXTENSIONS = {".txt", ".json", ".pdf", ".docx", ".doc"}
SUPPORTED_LAYOUT_EXTENSIONS = {".json"}


class ParseFileError(ValueError):
    """Raised when an uploaded file cannot be parsed."""


def _read_text_from_txt(content: bytes) -> str:
    """Read UTF-8 text content from a plain text file."""
    return content.decode("utf-8", errors="ignore").strip()


def _read_text_from_pdf(content: bytes) -> str:
    """Extract text from a PDF binary buffer."""
    try:
        from pypdf import PdfReader
    except ModuleNotFoundError as exc:
        raise ParseFileError(
            "Thiếu thư viện pypdf để đọc file .pdf. Hãy cài dependencies của dự án."
        ) from exc

    reader = PdfReader(io.BytesIO(content))
    parts: list[str] = []
    for page in reader.pages:
        parts.append((page.extract_text() or "").strip())
    return "\n".join(item for item in parts if item).strip()


def _read_text_from_docx(content: bytes) -> str:
    """Extract text from a DOCX binary buffer."""
    try:
        from docx import Document
    except ModuleNotFoundError as exc:
        raise ParseFileError(
            "Thiếu thư viện python-docx để đọc file .docx. Hãy cài dependencies của dự án."
        ) from exc

    document = Document(io.BytesIO(content))
    lines = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(lines).strip()


def extract_script_text(filename: str, content: bytes) -> str:
    """Extract script text from supported file formats."""
    suffix = Path(filename).suffix.lower()

    if suffix not in SUPPORTED_SCRIPT_EXTENSIONS:
        raise ParseFileError("Định dạng kịch bản không hỗ trợ. Chỉ chấp nhận txt, json, pdf, doc, docx.")

    if suffix == ".txt":
        result = _read_text_from_txt(content)
    elif suffix == ".json":
        data: Any = json.loads(content.decode("utf-8", errors="ignore"))
        result = json.dumps(data, ensure_ascii=False, indent=2)
    elif suffix == ".pdf":
        result = _read_text_from_pdf(content)
    elif suffix == ".docx":
        result = _read_text_from_docx(content)
    else:
        raise ParseFileError("File .doc (Word 97-2003) chưa được hỗ trợ. Vui lòng chuyển sang .docx.")

    if not result:
        raise ParseFileError("Không trích xuất được nội dung từ file kịch bản.")

    return result


def extract_layout_data(filename: str, content: bytes) -> list[dict]:
    """Extract panel layout data from a JSON file."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_LAYOUT_EXTENSIONS:
        raise ParseFileError("Bố cục chỉ hỗ trợ file JSON.")

    data = json.loads(content.decode("utf-8", errors="ignore"))

    if isinstance(data, dict) and "layout" in data and isinstance(data["layout"], list):
        layout = data["layout"]
    elif isinstance(data, list):
        layout = data
    else:
        raise ParseFileError("Dữ liệu bố cục không hợp lệ. Cần là list hoặc object có key 'layout'.")

    normalized: list[dict] = []
    for idx, item in enumerate(layout, start=1):
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "khung_so": int(item.get("khung_so", idx)),
                "aspect_ratio": normalize_aspect_ratio(item.get("aspect_ratio", DEFAULT_ASPECT_RATIO)),
                "image_size": normalize_image_size(item.get("image_size", DEFAULT_IMAGE_SIZE)),
            }
        )

    if not normalized:
        raise ParseFileError("File bố cục không có phần tử hợp lệ.")

    return normalized
