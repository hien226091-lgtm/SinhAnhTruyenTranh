"""Comic production endpoints."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi import File, Form, UploadFile

from api_base.app.config import CONFIG
from api_base.app.constants.image_options import DEFAULT_ASPECT_RATIO, aspect_ratio_to_legacy_key, normalize_aspect_ratio
from api_base.app.models.schemas import (
    CharacterUploadResponse,
    ImageOutput,
    PanelDraft,
    PageExportRequest,
    PageExportResponse,
    ParsedLayoutResponse,
    ParsedScriptResponse,
    PdfExportRequest,
    PdfExportResponse,
    ProductionRequest,
    ProductionResponse,
    ScriptAnalysisRequest,
    ScriptAnalysisResponse,
)
from api_base.app.utils.file_parsers import ParseFileError, extract_layout_data, extract_script_text
from api_base.app.utils.comic_postprocess import compose_episode_page, export_pdf_from_images, write_image_manifest
from api_base.app.utils.helpers import ensure_dir, sanitize_filename
from api_base.chatbot.services.story_writer import viet_kich_ban_chi_tiet, get_last_story_error
from api_base.chatbot.services.ai_generator import get_last_image_error, tao_anh_truyen_tranh


router = APIRouter(prefix="/comic", tags=["comic"])

def _validate_character_image(upload_file: UploadFile) -> None:
    """Validate uploaded character image extension."""
    suffix = Path(upload_file.filename or "").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ảnh nhân vật chỉ hỗ trợ png, jpg, jpeg, webp.",
        )


@router.post("/phan_tich_kich_ban", response_model=ScriptAnalysisResponse)
def phan_tich_kich_ban(payload: ScriptAnalysisRequest) -> ScriptAnalysisResponse:
    """Analyze a raw script and return panel drafts."""
    try:
        kich_ban_json = viet_kich_ban_chi_tiet(
            payload.text,
            so_khung=payload.frames,
            character_description=payload.character_description,
        )
    except Exception as exc:
        # Convert unexpected exceptions into a 503 so the frontend shows a friendly error.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "AI analysis failed with an internal error: " + str(exc)
            ),
        )

    if not kich_ban_json:
        last_err = get_last_story_error()
        if "RESOURCE_EXHAUSTED" in last_err.upper() or "prepayment credits" in last_err.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Gemini credit đã hết. Vui lòng nạp thêm credit tại https://ai.studio/projects. Chi tiết: {last_err}",
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"AI analysis failed. {last_err or 'Gemini API key is missing or not configured correctly. '}"
                "Set GEMINI_API_KEY or GOOGLE_AI_API_KEY in api_base/.env."
            ),
        )

    panels = []
    for item in kich_ban_json.get("kich_ban", []):
        panels.append(
            PanelDraft(
                mo_ta_hinh_anh=item.get("mo_ta_hinh_anh", ""),
                thoai_trai=item.get("thoai_trai", "..."),
                thoai_phai=item.get("thoai_phai", "..."),
                sfx=item.get("sfx", ""),
                aspect_ratio=normalize_aspect_ratio(item.get("aspect_ratio", DEFAULT_ASPECT_RATIO)),
                image_size=item.get("image_size", CONFIG.gemini_image_size),
            )
        )

    return ScriptAnalysisResponse(panels=panels)


@router.post("/upload-kich-ban", response_model=ParsedScriptResponse)
async def upload_kich_ban(file: UploadFile = File(...)) -> ParsedScriptResponse:
    """Upload and parse script content from txt/json/pdf/docx."""
    try:
        content = await file.read()
        text = extract_script_text(file.filename or "script.txt", content)
        return ParsedScriptResponse(text=text)
    except ParseFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lỗi đọc file kịch bản: {exc}") from exc


@router.post("/upload-layout", response_model=ParsedLayoutResponse)
async def upload_layout(file: UploadFile = File(...)) -> ParsedLayoutResponse:
    """Upload and parse user layout JSON."""
    try:
        content = await file.read()
        layout = extract_layout_data(file.filename or "layout.json", content)
        return ParsedLayoutResponse(layout=layout)
    except ParseFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lỗi đọc file bố cục: {exc}") from exc


@router.post("/upload-nhan-vat", response_model=CharacterUploadResponse)
async def upload_nhan_vat(
    session_id: str = Form("default"),
    files: list[UploadFile] = File(...),
) -> CharacterUploadResponse:
    """Upload character reference images and store them in inputs directory."""
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vui lòng tải lên ít nhất 1 ảnh nhân vật.")

    if len(files) > 14:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chỉ hỗ trợ tối đa 14 ảnh nhân vật tham chiếu.")

    safe_session_id = sanitize_filename(session_id)
    session_inputs_dir = ensure_dir(CONFIG.inputs_dir / "sessions" / safe_session_id)
    saved_files: list[str] = []

    for index, upload_file in enumerate(files, start=1):
        _validate_character_image(upload_file)
        suffix = Path(upload_file.filename or "").suffix.lower() or ".png"

        # Keep only the latest nhan_vat_{index}.* inside one session directory.
        for old_file in session_inputs_dir.glob(f"nhan_vat_{index}.*"):
            old_file.unlink(missing_ok=True)

        target_path = session_inputs_dir / f"nhan_vat_{index}{suffix}"

        content = await upload_file.read()
        try:
            target_path.write_bytes(content)
            saved_files.append(str(target_path.relative_to(CONFIG.inputs_dir)))
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lưu ảnh nhân vật thất bại: {exc}") from exc

    return CharacterUploadResponse(
        session_id=safe_session_id,
        files=saved_files,
        message="Đã cập nhật ảnh nhân vật tham chiếu thành công.",
    )


@router.post("/san_xuat", response_model=ProductionResponse)
def san_xuat_truyen(payload: ProductionRequest) -> ProductionResponse:
    """Produce individual images and return output image URLs."""
    ensure_dir(CONFIG.outputs_dir)

    images: list[str] = []
    notes: list[ImageOutput] = []
    for index, panel in enumerate(payload.panels, start=1):
        ten_file_vietsub = f"Anh_{index}.jpg"
        aspect_ratio_label = normalize_aspect_ratio(panel.aspect_ratio)
        aspect_ratio_key = aspect_ratio_to_legacy_key(aspect_ratio_label)

        path_final = tao_anh_truyen_tranh(
            panel.mo_ta_hinh_anh,
            ten_file_vietsub,
            aspect_ratio=aspect_ratio_label,
            image_size=panel.image_size,
            character_description=payload.character_description,
            session_id=payload.session_id,
            thoai_trai=panel.thoai_trai,
            thoai_phai=panel.thoai_phai,
            sfx=panel.sfx or "",
        )
        if not path_final:
            detail = get_last_image_error() or "AI render failed"
            detail_upper = detail.upper()
            la_loi_vertex_credentials = (
                "DEFAULT CREDENTIALS WERE NOT FOUND" in detail_upper
                or "APPLICATION DEFAULT CREDENTIALS" in detail_upper
                or "VERTEX AI CREDENTIALS" in detail_upper
            )
            la_loi_mang_tam_thoi = any(
                marker in detail_upper
                for marker in [
                    "CONNECTION ABORTED",
                    "REMOTEDISCONNECTED",
                    "MAX RETRIES EXCEEDED",
                    "HTTPSCONNECTIONPOOL",
                    "FAILED TO RESOLVE",
                    "NAME RESOLUTION",
                    "GETADDRINFO FAILED",
                    "TIMED OUT",
                    "TIMEOUT",
                ]
            )
            status_code = (
                status.HTTP_503_SERVICE_UNAVAILABLE
                if la_loi_vertex_credentials
                else (
                status.HTTP_429_TOO_MANY_REQUESTS
                if "RESOURCE_EXHAUSTED" in detail_upper or "QUOTA" in detail_upper
                else (status.HTTP_503_SERVICE_UNAVAILABLE if la_loi_mang_tam_thoi else status.HTTP_502_BAD_GATEWAY)
                )
            )
            raise HTTPException(
                status_code=status_code,
                detail=f"AI render failed at panel {index}: {detail}",
            )

        image_url = f"/outputs/{ten_file_vietsub}"
        images.append(image_url)
        notes.append(
            ImageOutput(
                filename=ten_file_vietsub,
                url=image_url,
                aspect_ratio_key=aspect_ratio_key,
                aspect_ratio_label=aspect_ratio_label,
            )
        )

        # Small pacing helps reduce burst rate-limit pressure on image APIs.
        if index < len(payload.panels):
            time.sleep(1.0)

    manifest_path = CONFIG.outputs_dir / "anh_manifest.json"
    write_image_manifest(manifest_path, [note.model_dump() for note in notes])

    return ProductionResponse(images=images, notes=notes, manifest_url=f"/outputs/{manifest_path.name}")


@router.post("/xuat-pdf", response_model=PdfExportResponse)
def xuat_pdf(payload: PdfExportRequest) -> PdfExportResponse:
    """Export selected generated images into a single PDF."""
    if not payload.images:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chưa chọn ảnh nào để xuất PDF.")

    image_paths: list[str] = []
    for item in payload.images:
        filename = Path(item).name
        path = CONFIG.outputs_dir / filename
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Không tìm thấy ảnh: {filename}")
        image_paths.append(str(path))

    pdf_name = f"anh_da_chon_{time.time_ns()}.pdf"
    pdf_path = CONFIG.outputs_dir / pdf_name
    export_pdf_from_images(image_paths, pdf_path)

    return PdfExportResponse(pdf_url=f"/outputs/{pdf_name}", filename=pdf_name, image_count=len(image_paths))


@router.post("/xuat-trang", response_model=PageExportResponse)
def xuat_trang(payload: PageExportRequest) -> PageExportResponse:
    """Compose selected generated images into one page (maximum 8 panels)."""
    if not payload.images:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chưa chọn ảnh nào để ghép trang.")

    if len(payload.images) > 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Một trang chỉ hỗ trợ tối đa 8 khung.")

    image_paths: list[str] = []
    for item in payload.images:
        filename = Path(item).name
        path = CONFIG.outputs_dir / filename
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Không tìm thấy ảnh: {filename}")
        image_paths.append(str(path))

    page_name = f"trang_ghep_{time.time_ns()}.jpg"
    page_path = CONFIG.outputs_dir / page_name
    columns = min(4, max(1, len(image_paths)))
    compose_episode_page(image_paths, page_path, columns=columns, panel_border=4, gap=8, margin=10)

    return PageExportResponse(page_url=f"/outputs/{page_name}", filename=page_name, image_count=len(image_paths))
