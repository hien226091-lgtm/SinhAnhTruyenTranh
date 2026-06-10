"""Pydantic schemas for request and response validation."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from api_base.app.constants.image_options import DEFAULT_ASPECT_RATIO, DEFAULT_IMAGE_SIZE, normalize_aspect_ratio, normalize_image_size


class HealthResponse(BaseModel):
    """Health check response payload."""
    status: str


class LoginRequest(BaseModel):
    """Credentials for login."""
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    """Payload to create a new user."""
    username: str = Field(..., min_length=3)
    email: str = Field(...)  # Đã thêm trường email để khớp với Database
    password: str = Field(..., min_length=6)
    fullname: str | None = None


class RegisterResponse(BaseModel):
    message: str


class UserProfile(BaseModel):
    username: str
    email: str
    fullname: str | None = None


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class ScriptAnalysisRequest(BaseModel):
    """Request payload for script analysis."""
    text: str = Field(..., min_length=1)
    frames: int = Field(4, ge=1, le=12)
    character_description: str = ""
    layout_json: Optional[str] = None


class PanelDraft(BaseModel):
    """Panel draft data for the client UI."""
    mo_ta_hinh_anh: str
    thoai_trai: str
    thoai_phai: str
    sfx: Optional[str] = ""
    aspect_ratio: str = DEFAULT_ASPECT_RATIO
    image_size: str = DEFAULT_IMAGE_SIZE

    @field_validator("aspect_ratio")
    @classmethod
    def _normalize_aspect_ratio(cls, value: str) -> str:
        return normalize_aspect_ratio(value)

    @field_validator("image_size")
    @classmethod
    def _normalize_image_size(cls, value: str) -> str:
        return normalize_image_size(value)


class ScriptAnalysisResponse(BaseModel):
    """Response payload for script analysis."""
    comic_id: Optional[int] = None  # Cầu nối để báo cho Frontend biết ID của truyện vừa tạo
    panels: List[PanelDraft]


class ProductionRequest(BaseModel):
    """Request payload for producing comic panels."""
    comic_id: Optional[int] = None  # Frontend sẽ gửi ID truyện xuống để Server lưu khung ảnh vào DB
    panels: List[PanelDraft]
    character_description: str = ""
    session_id: str = "default"


class LayoutItem(BaseModel):
    """Single layout item uploaded by the user."""
    khung_so: int
    aspect_ratio: str
    image_size: str = DEFAULT_IMAGE_SIZE

    @field_validator("aspect_ratio")
    @classmethod
    def _normalize_layout_aspect_ratio(cls, value: str) -> str:
        return normalize_aspect_ratio(value)

    @field_validator("image_size")
    @classmethod
    def _normalize_layout_image_size(cls, value: str) -> str:
        return normalize_image_size(value)


class ParsedScriptResponse(BaseModel):
    """Response payload for parsed script file uploads."""
    text: str


class ParsedLayoutResponse(BaseModel):
    """Response payload for parsed layout file uploads."""
    layout: List[LayoutItem]


class CharacterUploadResponse(BaseModel):
    """Response payload for character image uploads."""
    comic_id: Optional[int] = None # Thêm ID truyện
    session_id: str
    files: List[str]
    message: str


class ImageOutput(BaseModel):
    """Output metadata for one generated image."""
    filename: str
    url: str
    aspect_ratio_key: str
    aspect_ratio_label: str


class ProductionResponse(BaseModel):
    """Response payload for production output."""
    images: List[str]
    notes: List[ImageOutput] = []
    manifest_url: str = ""


class PdfExportRequest(BaseModel):
    """Request payload for exporting selected images to PDF."""
    images: List[str]


class PdfExportResponse(BaseModel):
    """Response payload for PDF export."""
    pdf_url: str
    filename: str
    image_count: int


class PageExportRequest(BaseModel):
    """Request payload for exporting selected images into one composed page."""
    images: List[str]


class PageExportResponse(BaseModel):
    """Response payload for one composed page export."""
    page_url: str
    filename: str
    image_count: int


class UploadResponse(BaseModel):
    """Response payload for file uploads."""
    filename: str
    url: str