"""Google Vertex AI-based image generation service."""

from __future__ import annotations

import time
import os
from pathlib import Path
from typing import List, Optional

import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from PIL import Image, ImageDraw, ImageFont
import textwrap

from api_base.app.config import CONFIG
from api_base.app.constants.image_options import DEFAULT_ASPECT_RATIO, normalize_aspect_ratio, normalize_image_size
from api_base.app.utils.helpers import sanitize_filename

# Khởi tạo Vertex AI
vertexai.init(project=CONFIG.vertex_project_id, location=CONFIG.vertex_location)

def _session_inputs_dir(session_id: str) -> Path:
    return CONFIG.inputs_dir / "sessions" / sanitize_filename(session_id)

def _tai_anh_tham_chieu(session_id: str = "default") -> tuple[List[Image.Image], bool]:
    session_dir = _session_inputs_dir(session_id)
    images = []
    if session_dir.exists():
        for p in session_dir.iterdir():
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                images.append(Image.open(p))
    return images, bool(images)

class VertexImageGenerator:
    def __init__(self) -> None:
        self.last_error: str = ""

    def generate(self, prompt: str, output_path: str, aspect_ratio: str) -> Optional[str]:
        self.last_error = ""
        # Đồng bộ: Dùng model từ config (đã set là imagen-3.0-fast-generate)
        model_name = CONFIG.vertex_image_models[0]
        
        try:
            model = ImageGenerationModel.from_pretrained(model_name)
            time.sleep(1) 
            
            images = model.generate_images(
                prompt=prompt,
                number_of_images=1,
                aspect_ratio=aspect_ratio,
            )
            
            if images:
                images[0].save(location=output_path)
                return output_path
        except Exception as e:
            self.last_error = str(e)
            print(f"Lỗi Vertex AI: {self.last_error}")
        return None

_generator = VertexImageGenerator()

def tao_anh_truyen_tranh(
    kich_ban: str, 
    ten_file_dau_ra: str = "hinh_1.jpg", 
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    image_size: str = "2K",
    character_description: str = "",
    session_id: str = "default",
    thoai_trai: str = "...", 
    thoai_phai: str = "...", 
    sfx: str = ""
) -> Optional[str]:
    
    path_dau_ra = CONFIG.outputs_dir / ten_file_dau_ra
    
    # Prompt đồng bộ với yêu cầu mới: Linh hoạt, không tên cố định
    prompt = f"""
    Create a professional comic panel based on: {kich_ban}.
    
    CHARACTER CONSISTENCY: Use these details/reference: {character_description}.
    Maintain stable face, outfit, and identity.
    
    LAYOUT: 
    - Draw exactly 2 speech bubbles (Top-left: "{thoai_trai}", Top-right: "{thoai_phai}").
    - SFX text: "{sfx}".
    - Bubbles MUST be empty (we will overlay text later).
    
    ART STYLE: High-quality 2D anime/comic, clean bold lines, cel-shading.
    """.strip()
    
    path = _generator.generate(
        prompt=prompt,
        output_path=str(path_dau_ra),
        aspect_ratio=normalize_aspect_ratio(aspect_ratio)
    )
    
    return path

def get_last_image_error() -> str:
    return _generator.last_error