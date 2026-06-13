"""Comic production endpoints."""

from __future__ import annotations

import io
import json
import time
import zipfile
from datetime import datetime
from pathlib import Path
from api_base.app.security.admin_deps import verify_admin
from api_base.app.security.deps import get_current_user
from fastapi import APIRouter, HTTPException, status, Depends, Body
from fastapi import File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from api_base.app.config import CONFIG
from api_base.app.constants.image_options import DEFAULT_ASPECT_RATIO, aspect_ratio_to_legacy_key, normalize_aspect_ratio
from api_base.app.models.schemas import (
    CharacterUploadResponse,
    ComicSession,
    FrameItem,
    GenerationHistoryResponse,
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
    TopupHistoryResponse,
    TopupRecord,
)
from api_base.app.utils.file_parsers import ParseFileError, extract_layout_data, extract_script_text
from api_base.app.utils.comic_postprocess import compose_episode_page, export_pdf_from_images, write_image_manifest
from api_base.app.utils.helpers import ensure_dir, get_user_dir, sanitize_filename
from api_base.app.utils.quota_manager import FREE_PLAN_LIMIT, PRO_PLAN_LIMIT, check_quota_and_log, check_generation_quota, get_plan_limit, increment_generated_count
from api_base.chatbot.services.story_writer import viet_kich_ban_chi_tiet, get_last_story_error
from api_base.chatbot.services.ai_generator import get_last_image_error, tao_anh_truyen_tranh


def _resolve_image_path(url_or_path: str) -> Path:
    """Resolve an image URL/path to an actual file under outputs_dir.

    Handles both:
      /outputs/User_VoVanHien/Anh_1.jpg  -> outputs/User_VoVanHien/Anh_1.jpg
      Anh_1.jpg                          -> outputs/Anh_1.jpg
    """
    path = Path(url_or_path)
    # If it starts with /outputs/ or outputs/, strip that prefix
    str_path = url_or_path.replace("\\", "/")
    if "/outputs/" in str_path:
        relative = str_path.split("/outputs/", 1)[1]
        path = CONFIG.outputs_dir / relative
    elif not path.is_absolute():
        path = CONFIG.outputs_dir / path
    resolved = path.resolve()
    # Prevent path traversal
    outputs_resolved = CONFIG.outputs_dir.resolve()
    if outputs_resolved not in resolved.parents and resolved != outputs_resolved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Đường dẫn ảnh không hợp lệ")
    return resolved

# KẾT NỐI DATABASE
from api_base.app.models.base_db import get_db
from api_base.app.models.schema_db import Comic, Character, Frame, RequestLog, User 

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
def phan_tich_kich_ban(
    payload: ScriptAnalysisRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Chốt chặn bảo mật
) -> ScriptAnalysisResponse:
    """Analyze a raw script and return panel drafts, then save to DB."""
    try:
        # 1. Gọi AI phân tích kịch bản
        kich_ban_json = viet_kich_ban_chi_tiet(
            payload.text,
            so_khung=payload.frames,
            character_description=payload.character_description,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analysis failed with an internal error: " + str(exc),
        )

    # 2. Kiểm tra nếu AI trả về lỗi
    if not kich_ban_json:
        last_err = get_last_story_error()
        if "RESOURCE_EXHAUSTED" in last_err.upper() or "prepayment credits" in last_err.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Gemini credit đã hết. Chi tiết: {last_err}",
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI analysis failed. {last_err}",
        )

    # 3. Xử lý dữ liệu trả về từ AI
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

    # 4. LƯU DỰ ÁN VÀO DATABASE (Với UserID từ current_user)
    try:
        new_comic = Comic(
            UserID=current_user.UserID, 
            Title=payload.title,
            ScriptContent=payload.text,
            LayoutJsonPath=getattr(payload, 'layout_json', None) 
        )
        db.add(new_comic)
        db.commit()
        db.refresh(new_comic)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi lưu dự án vào cơ sở dữ liệu: " + str(exc)
        )

    return ScriptAnalysisResponse(comic_id=new_comic.ComicID, panels=panels)


@router.post("/upload-kich-ban", response_model=ParsedScriptResponse)
async def upload_kich_ban(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> ParsedScriptResponse:
    """Upload and parse script content from txt/json/pdf/docx. Chặn người chưa đăng nhập."""
    
    try:
        content = await file.read()
        text = extract_script_text(file.filename or "script.txt", content)
        return ParsedScriptResponse(text=text)
    except ParseFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lỗi đọc file kịch bản: {exc}") from exc


@router.post("/upload-layout", response_model=ParsedLayoutResponse)
async def upload_layout(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> ParsedLayoutResponse:
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
    comic_id: int = Form(None),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CharacterUploadResponse:
    """Upload character reference images to user-specific folder."""
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vui lòng tải lên ít nhất 1 ảnh nhân vật.")

    # Tạo thư mục input cá nhân cho user
    user_input_dir = get_user_dir(CONFIG.inputs_dir, current_user.FullName or "Guest")
    safe_session_id = sanitize_filename(session_id)
    session_dir = ensure_dir(user_input_dir / "sessions" / safe_session_id)
    
    saved_files: list[str] = []

    for index, upload_file in enumerate(files, start=1):
        _validate_character_image(upload_file)
        suffix = Path(upload_file.filename or "").suffix.lower() or ".png"
        target_path = session_dir / f"nhan_vat_{index}_{int(time.time())}{suffix}"
        
        content = await upload_file.read()
        target_path.write_bytes(content)
        
        # Lưu đường dẫn tương đối để dễ quản lý
        file_url = str(target_path.relative_to(CONFIG.inputs_dir))
        saved_files.append(file_url)
        
        if comic_id:
            new_char = Character(ComicID=comic_id, ReferenceImages=file_url)
            db.add(new_char)

    if comic_id:
        db.commit()

    return CharacterUploadResponse(
        comic_id=comic_id,
        session_id=safe_session_id,
        files=saved_files,
        message="Đã cập nhật ảnh nhân vật vào thư mục cá nhân."
    )


@router.post("/san_xuat", response_model=ProductionResponse)
def san_xuat_truyen(
    payload: ProductionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ProductionResponse:
    """Produce individual images and save frames to DB in user-specific folder."""
    # Check plan-based generation quota
    allowed, msg = check_generation_quota(db, current_user)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=msg)

    if not check_quota_and_log(db, current_user.UserID, "imagen-4.0"):
        raise HTTPException(
            status_code=429, 
            detail="Bạn đang vẽ quá nhanh! Hãy chờ 1 phút để hệ thống làm mới hạn mức nhé."
        )
    # Tạo thư mục riêng cho user
    user_output_dir = get_user_dir(CONFIG.outputs_dir, current_user.FullName or "Guest")

    images: list[str] = []
    notes: list[ImageOutput] = []
    VALID_ASPECT_RATIOS = ["1:1", "3:4", "4:3", "9:16", "16:9"]

    for index, panel in enumerate(payload.panels, start=1):
        ten_file_vietsub = f"Anh_{payload.comic_id or 'default'}_{index}_{int(time.time())}.jpg"
        
        aspect_ratio_label = normalize_aspect_ratio(panel.aspect_ratio)
        if aspect_ratio_label not in VALID_ASPECT_RATIOS:
            aspect_ratio_label = "16:9"
            
        aspect_ratio_key = aspect_ratio_to_legacy_key(aspect_ratio_label)

        # Lưu vào thư mục của user
        path_final = None
        max_retries = 3
        
        for attempt in range(max_retries):
            # Lưu ý: Bạn cần đảm bảo tao_anh_truyen_tranh hỗ trợ nhận đường dẫn folder đích
            # Nếu không, hãy tạo file tại user_output_dir / ten_file_vietsub
            path_final = tao_anh_truyen_tranh(
                panel.mo_ta_hinh_anh,
                str(user_output_dir / ten_file_vietsub), 
                aspect_ratio=aspect_ratio_label,
                image_size=panel.image_size,
                character_description=payload.character_description,
                session_id=payload.session_id,
                thoai_trai=panel.thoai_trai,
                thoai_phai=panel.thoai_phai,
                sfx=panel.sfx or "",
            )
            if path_final: break
            
            detail = get_last_image_error() or "AI render failed"
            if "429" in detail or "QUOTA" in detail.upper():
                time.sleep(45.0)
                continue
            break

        if not path_final:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Lỗi vẽ khung {index}")

        # Tạo URL với tên thư mục user để frontend truy cập đúng
        image_url = f"/outputs/{user_output_dir.name}/{ten_file_vietsub}"
        images.append(image_url)
        notes.append(ImageOutput(filename=ten_file_vietsub, url=image_url, aspect_ratio_key=aspect_ratio_key, aspect_ratio_label=aspect_ratio_label))

        if payload.comic_id:
            new_frame = Frame(
                ComicID=payload.comic_id,
                FrameOrder=index,
                AspectRatio=aspect_ratio_label,
                Resolution=panel.image_size,
                ImageDescription=panel.mo_ta_hinh_anh,
                DialogLeft=panel.thoai_trai,
                DialogRight=panel.thoai_phai,
                SFX=panel.sfx,
                GeneratedImageUrl=image_url
            )
            db.add(new_frame)
            db.commit()

        increment_generated_count(db, current_user)

        if index < len(payload.panels):
            time.sleep(20.0)

    manifest_path = user_output_dir / f"anh_manifest_{payload.comic_id or 'default'}.json"
    write_image_manifest(manifest_path, [note.model_dump() for note in notes])

    return ProductionResponse(images=images, notes=notes, manifest_url=f"/outputs/{user_output_dir.name}/{manifest_path.name}")


@router.post("/xuat-pdf", response_model=PdfExportResponse)
def xuat_pdf(
    payload: PdfExportRequest,
    current_user: User = Depends(get_current_user)
    ) -> PdfExportResponse:
    """Export selected generated images into a single PDF."""
    if not payload.images:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chưa chọn ảnh nào để xuất PDF.")

    image_paths: list[str] = []
    for item in payload.images:
        path = _resolve_image_path(item)
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Không tìm thấy ảnh: {path.name}")
        image_paths.append(str(path))

    pdf_name = f"anh_da_chon_{time.time_ns()}.pdf"
    pdf_path = CONFIG.outputs_dir / pdf_name
    export_pdf_from_images(image_paths, pdf_path)

    return PdfExportResponse(pdf_url=f"/outputs/{pdf_name}", filename=pdf_name, image_count=len(image_paths))


@router.post("/xuat-zip")
def xuat_zip(
    payload: PdfExportRequest,
    current_user: User = Depends(get_current_user)
    ):
    """Download selected images as a ZIP file."""
    if not payload.images:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chưa chọn ảnh nào để tải ZIP.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in payload.images:
            path = _resolve_image_path(item)
            if not path.exists():
                continue
            zf.write(path, arcname=path.name)

    buf.seek(0)
    zip_name = f"anh_da_chon_{time.time_ns()}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


@router.post("/xuat-trang", response_model=PageExportResponse)
def xuat_trang(
    payload: PageExportRequest, 
    current_user: User = Depends(get_current_user)
    ) -> PageExportResponse:
    """Compose selected generated images into one page (maximum 8 panels)."""
    if not payload.images:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chưa chọn ảnh nào để ghép trang.")
    if len(payload.images) > 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Một trang chỉ hỗ trợ tối đa 8 khung.")

    image_paths: list[str] = []
    for item in payload.images:
        path = _resolve_image_path(item)
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Không tìm thấy ảnh: {path.name}")
        image_paths.append(str(path))

    page_name = f"trang_ghep_{time.time_ns()}.jpg"
    page_path = CONFIG.outputs_dir / page_name
    columns = min(4, max(1, len(image_paths)))
    compose_episode_page(image_paths, page_path, columns=columns, panel_border=4, gap=8, margin=10)

    return PageExportResponse(page_url=f"/outputs/{page_name}", filename=page_name, image_count=len(image_paths))

@router.get("/admin/users")
def get_users(db: Session = Depends(get_db), admin: User = Depends(verify_admin)):
    """Lấy danh sách toàn bộ người dùng cho Admin."""
    return db.query(User).all()

@router.get("/admin/stats")
def xem_thong_ke(
    db: Session = Depends(get_db),
    admin: User = Depends(verify_admin) # Chỉ cần gắn cái này, không cần if-else nữa
):
    stats = db.query(
        RequestLog.UserID, 
        func.count(RequestLog.LogID).label("total_requests")
    ).group_by(RequestLog.UserID).all()
    
    return {"stats": [{"user_id": s[0], "count": s[1]} for s in stats]}

@router.post("/admin/ban_user/{user_id}")
def ban_user(
    user_id: int, 
    is_banned: bool, 
    db: Session = Depends(get_db), 
    admin: User = Depends(verify_admin) # Chỉ cần cái này là đủ
):
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy user!")
    
    user.is_banned = is_banned
    db.commit()
    return {"message": "Success"}

@router.get("/plan-status")
def plan_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return current user's plan info and remaining quota."""
    limit = get_plan_limit(current_user.Plan or "free")
    used = current_user.ImagesGenerated or 0
    remaining = max(0, limit - used)
    return {
        "plan": current_user.Plan or "free",
        "limit": limit,
        "used": used,
        "remaining": remaining,
        "is_pro": (current_user.Plan == "pro"),
    }

# API cấp thêm lượt vẽ cho User
@router.post("/admin/grant_quota/{user_id}")
def grant_quota(
    user_id: int, 
    extra_quota: int, 
    db: Session = Depends(get_db), 
    admin: User = Depends(verify_admin)
):
    # Giả sử bạn có bảng User hoặc Quota, ở đây tui ví dụ cập nhật trực tiếp vào User
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    
    # Bạn cần đảm bảo trong model User có trường Quota
    user.Quota = (user.Quota or 0) + extra_quota
    db.commit()
    return {"message": f"Đã cấp thêm {extra_quota} lượt vẽ cho User {user_id}"}

@router.post("/admin/upgrade/{user_id}")
def upgrade_user(
    user_id: int,
    plan: str = "pro",
    db: Session = Depends(get_db),
    admin: User = Depends(verify_admin)
):
    """Upgrade/downgrade a user's plan."""
    if plan not in ("free", "pro"):
        raise HTTPException(status_code=400, detail="Plan must be 'free' or 'pro'")
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    user.Plan = plan
    db.commit()
    return {"message": f"Đã chuyển User {user_id} sang gói {plan}"}

@router.post("/self-upgrade")
def self_upgrade(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """User tự nâng cấp lên Pro sau khi chuyển khoản."""
    if current_user.Plan == "pro":
        raise HTTPException(status_code=400, detail="Bạn đã là thành viên Pro rồi!")
    transaction_ref = (body.get("transaction_ref") or "").strip()
    current_user.Plan = "pro"
    current_user.UpgradedAt = datetime.utcnow()
    current_user.TransactionRef = transaction_ref or None
    db.commit()
    print(f"[UPGRADE] User {current_user.UserID} ({current_user.Email}) tự nâng cấp lên Pro. Ref: {transaction_ref}")
    return {"message": "Chúc mừng! Bạn đã nâng cấp lên gói Pro thành công. 🎉"}

@router.get("/history", response_model=GenerationHistoryResponse)
def generation_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return generation history: comics with frames for the current user."""
    comics = db.query(Comic).filter(Comic.UserID == current_user.UserID).order_by(Comic.CreatedAt.desc()).all()
    sessions = []
    for comic in comics:
        frames = db.query(Frame).filter(Frame.ComicID == comic.ComicID).order_by(Frame.FrameOrder).all()
        sessions.append(ComicSession(
            comic_id=comic.ComicID,
            title=comic.Title or "Truyện tranh",
            created_at=str(comic.CreatedAt) if comic.CreatedAt else "",
            frame_count=len(frames),
            frames=[FrameItem(
                frame_id=f.FrameID,
                frame_order=f.FrameOrder,
                image_url=f.GeneratedImageUrl or None,
                description=(f.ImageDescription or "")[:120],
            ) for f in frames],
        ))
    return GenerationHistoryResponse(sessions=sessions)


@router.get("/topup-history", response_model=TopupHistoryResponse)
def topup_history(current_user: User = Depends(get_current_user)):
    """Return top-up/payment history for the current user."""
    records = []
    if current_user.UpgradedAt:
        records.append(TopupRecord(
            date=str(current_user.UpgradedAt),
            plan="pro",
            transaction_ref=current_user.TransactionRef or None,
            amount="199.999 VNĐ",
        ))
    return TopupHistoryResponse(records=records)


@router.delete("/history/{comic_id}")
def xoa_truyen_ca_nhan(
    comic_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a comic/session owned by the current user."""
    comic = db.query(Comic).filter(Comic.ComicID == comic_id, Comic.UserID == current_user.UserID).first()
    if not comic:
        raise HTTPException(status_code=404, detail="Không tìm thấy truyện hoặc không có quyền xóa.")
    frames = db.query(Frame).filter(Frame.ComicID == comic_id).all()
    for f in frames:
        db.delete(f)
    db.delete(comic)
    db.commit()
    return {"message": "Đã xóa truyện thành công."}


@router.get("/history/{comic_id}/manifest")
def tai_manifest(
    comic_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return manifest JSON for a comic session."""
    comic = db.query(Comic).filter(Comic.ComicID == comic_id, Comic.UserID == current_user.UserID).first()
    if not comic:
        raise HTTPException(status_code=404, detail="Không tìm thấy truyện.")
    frames = db.query(Frame).filter(Frame.ComicID == comic_id).order_by(Frame.FrameOrder).all()
    manifest = {
        "comic_id": comic.ComicID,
        "title": comic.Title or "Truyện tranh",
        "created_at": str(comic.CreatedAt) if comic.CreatedAt else "",
        "frames": [
            {
                "frame_order": f.FrameOrder,
                "image_url": f.GeneratedImageUrl,
                "description": f.ImageDescription,
                "dialog_left": f.DialogLeft,
                "dialog_right": f.DialogRight,
                "sfx": f.SFX,
                "aspect_ratio": f.AspectRatio,
                "resolution": f.Resolution,
            }
            for f in frames
        ],
    }
    manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2)
    return StreamingResponse(
        io.BytesIO(manifest_json.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="manifest_{comic_id}.json"'},
    )


# ── Admin: Cấu hình hệ thống ──

CONFIG_CATEGORIES = {
    "Vertex AI": ["VERTEX_PROJECT_ID", "VERTEX_LOCATION", "VERTEX_TEXT_MODEL", "VERTEX_IMAGE_MODELS", "VERTEX_CREDENTIALS_FILE"],
    "Google AI": ["GOOGLE_AI_API_KEY", "GEMINI_IMAGE_MODELS", "GEMINI_IMAGE_SIZE"],
    "Xác thực": ["JWT_SECRET", "JWT_ALGORITHM", "JWT_EXPIRE_MINUTES", "ADMIN_USERNAME", "ADMIN_PASSWORD_HASH", "PASSWORD_SALT"],
    "OAuth": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET", "OAUTH_REDIRECT_BASE"],
    "Khác": ["ALLOWED_ORIGINS"],
}

_ENV_PATH = CONFIG.base_dir / ".env"


def _validate_vertex_config(values: dict) -> list[str]:
    """Kiểm tra cấu hình Vertex AI và trả về danh sách lỗi."""
    errors: list[str] = []
    project = values.get("VERTEX_PROJECT_ID", "").strip()
    location = values.get("VERTEX_LOCATION", "").strip()
    cred_file = values.get("VERTEX_CREDENTIALS_FILE", "").strip()

    if not project:
        errors.append("Vertex AI: VERTEX_PROJECT_ID đang để trống.")
    if not location:
        errors.append("Vertex AI: VERTEX_LOCATION đang để trống.")

    if cred_file:
        cred_path = Path(cred_file).expanduser()
        if not cred_path.exists():
            errors.append(f"Vertex AI: File credentials không tồn tại ({cred_file}).")
        elif not cred_path.is_file():
            errors.append(f"Vertex AI: Đường dẫn credentials không phải là file ({cred_file}).")

    # Thử kết nối nếu có đủ thông tin
    if project and location:
        try:
            from google import genai
            kwargs: dict = {"vertexai": True, "project": project, "location": location}
            if cred_file:
                from google.oauth2 import service_account
                cred_path = Path(cred_file).expanduser()
                if cred_path.exists():
                    kwargs["credentials"] = service_account.Credentials.from_service_account_file(str(cred_path))
            client = genai.Client(**kwargs)
            # Thử gọi API nhẹ để kiểm tra kết nối thực tế
            for m in client.models.list():
                break
        except Exception as e:
            msg = str(e)
            if "403" in msg or "permission" in msg.lower():
                errors.append(f"Vertex AI: Không có quyền truy cập — kiểm tra credentials hoặc tài khoản service.")
            elif "404" in msg or "not found" in msg.lower():
                errors.append(f"Vertex AI: Project không tồn tại hoặc location không đúng.")
            elif "401" in msg or "unauthorized" in msg.lower():
                errors.append(f"Vertex AI: Xác thực thất bại — credentials không hợp lệ.")
            else:
                errors.append(f"Vertex AI: {msg}")
    return errors


def _validate_google_ai_config(values: dict) -> list[str]:
    """Kiểm tra cấu hình Google AI API key."""
    errors: list[str] = []
    api_key = values.get("GOOGLE_AI_API_KEY", "").strip()
    if api_key:
        if len(api_key) < 10:
            errors.append("Google AI: API key có vẻ không hợp lệ (quá ngắn).")
        elif not api_key.startswith("AI"):
            errors.append("Google AI: API key thường bắt đầu bằng 'AI' — kiểm tra lại.")
    return errors


def _validate_oauth_config(values: dict) -> list[str]:
    """Kiểm tra định dạng OAuth URLs."""
    errors: list[str] = []
    redirect = values.get("OAUTH_REDIRECT_BASE", "").strip()
    if redirect and not redirect.startswith("http"):
        errors.append("OAuth: OAUTH_REDIRECT_BASE phải bắt đầu bằng http:// hoặc https://.")
    return errors


def _validate_env_config(values: dict) -> list[str]:
    """Kiểm tra toàn bộ cấu hình .env và trả về danh sách lỗi."""
    all_errors: list[str] = []
    all_errors.extend(_validate_vertex_config(values))
    all_errors.extend(_validate_google_ai_config(values))
    all_errors.extend(_validate_oauth_config(values))

    # Kiểm tra JWT secret còn mặc định
    jwt = values.get("JWT_SECRET", "").strip()
    if jwt in ("change-me", ""):
        all_errors.append("Xác thực: JWT_SECRET đang để mặc định 'change-me' — nên thay đổi để bảo mật.")
    return all_errors


@router.get("/admin/config")
def admin_get_config(admin: User = Depends(verify_admin)):
    """Read .env file and return config values."""
    config: dict[str, str] = {}
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text("utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            config[key.strip()] = val.strip().strip('"').strip("'")
    return {"config": config, "categories": CONFIG_CATEGORIES}


@router.post("/admin/config")
def admin_save_config(
    body: dict,
    admin: User = Depends(verify_admin),
):
    """Update .env file and validate API configuration."""
    updates = body.get("config", {})
    if not _ENV_PATH.exists():
        raise HTTPException(status_code=404, detail="File .env không tồn tại.")

    # Ghi file
    lines = _ENV_PATH.read_text("utf-8").splitlines()
    new_lines: list[str] = []
    updated_keys: set[str] = set()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        key, _, _ = stripped.partition("=")
        key = key.strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            updated_keys.add(key)
        else:
            new_lines.append(line)

    for key, val in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}")

    _ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    # Validate sau khi lưu
    merged = dict(updates)
    for line in new_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, val = stripped.partition("=")
        key = key.strip()
        if key not in merged:
            merged[key] = val.strip().strip('"').strip("'")

    warnings = _validate_env_config(merged)

    message = "Đã lưu cấu hình. Khởi động lại server để áp dụng thay đổi."
    if not warnings:
        message += " Kiểm tra kết nối OK."
    else:
        message += " Có cảnh báo:"
    return {"message": message, "updated": list(updates.keys()), "warnings": warnings}


# API lấy nhật ký hệ thống (để xem User nào vẽ nhiều nhất)
@router.get("/admin/logs")
def get_logs(db: Session = Depends(get_db), admin: User = Depends(verify_admin)):
    logs = db.query(RequestLog).order_by(RequestLog.LogID.desc()).limit(50).all()
    return logs

@router.get("/admin/all_comics")
def get_all_comics(db: Session = Depends(get_db), admin: User = Depends(verify_admin)):
    # Lấy danh sách truyện kèm thông tin User tạo ra nó
    comics = db.query(Comic).all()
    return comics

@router.delete("/admin/delete_comic/{comic_id}")
def delete_comic(comic_id: int, db: Session = Depends(get_db), admin: User = Depends(verify_admin)):
    comic = db.query(Comic).filter(Comic.ComicID == comic_id).first()
    if not comic:
        raise HTTPException(status_code=404, detail="Không tìm thấy truyện")
    db.delete(comic)
    db.commit()
    return {"message": "Đã xóa truyện thành công"}