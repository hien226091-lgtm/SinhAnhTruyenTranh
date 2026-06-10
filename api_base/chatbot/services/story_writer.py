"""Vertex AI based script writing service."""

from __future__ import annotations

import json
import os
from typing import Optional

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

from api_base.app.config import CONFIG

class VertexStoryWriter:
    """Generate structured story scripts using Vertex AI."""

    def __init__(self) -> None:
        self.last_error: str = ""
        try:
            # Khởi tạo Vertex AI với Project ID và Location từ file .env
            vertexai.init(project=CONFIG.vertex_project_id, location=CONFIG.vertex_location)
            
            # Ưu tiên lấy model từ VERTEX_TEXT_MODEL, nếu không có thì mặc định xài gemini-1.5-flash-002
            model_name = getattr(CONFIG, 'vertex_text_model', 'gemini-1.5-flash-002')
            self._model = GenerativeModel(model_name)
            print(f"[story_writer] Kết nối thành công Vertex AI (project={CONFIG.vertex_project_id}, location={CONFIG.vertex_location}, model={model_name})")
        except Exception as exc:
            print(f"[story_writer] Lỗi khởi tạo Vertex AI: {exc}")
            self._model = None

    def generate(self, prompt: str) -> Optional[dict]:
        """Generate a story script from the prompt."""
        self.last_error = ""

        if not self._model:
            self.last_error = "Vertex AI chưa được khởi tạo. Hãy kiểm tra lại Credentials và file .env."
            print(f"Lỗi: {self.last_error}")
            return None

        try:
            # Ép Vertex AI phải trả về định dạng JSON
            generation_config = GenerationConfig(response_mime_type="application/json")
            response = self._model.generate_content(prompt, generation_config=generation_config)

            text = response.text.strip()
            if not text:
                self.last_error = "AI không trả về kết quả nào."
                return None

            # Dọn dẹp rác markdown (nếu có)
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            try:
                return json.loads(text.strip())
            except Exception as exc2:
                self.last_error = f"Lỗi dịch chuỗi JSON: {exc2}"
                print(self.last_error)
                print("Nội dung AI trả về (bị lỗi):", text[:2000])
                return None

        except Exception as exc:
            self.last_error = str(exc)
            print("\n=== CHI TIẾT LỖI VERTEX AI ===")
            print(f"Loại lỗi: {type(exc).__name__}")
            print(f"Tin nhắn lỗi: {self.last_error}")
            print("==============================\n")
            return None

# Khởi tạo trực tiếp writer dùng Vertex AI
_writer = VertexStoryWriter()

DEFAULT_CHARACTER_GUIDE = """
- Nhân vật 1: Tên (vd: Anh Tu) — mô tả ngắn (ngoại hình, trang phục, tính cách, vai trò).
- Nhân vật 2: Tên (vd: Be Trau) — mô tả ngắn (ngoại hình, trang phục, tính cách, vai trò).
""".strip()

def _build_character_guide(character_description: str) -> str:
    """Build a character guide that can be reused across prompts."""
    cleaned = (character_description or "").strip()
    if cleaned:
        return cleaned
    return DEFAULT_CHARACTER_GUIDE

def viet_kich_ban_chi_tiet(
    y_tuong: str,
    so_khung: int = 6,
    character_description: str = "",
) -> Optional[dict]:
    """Generate a detailed comic script with panel-level data using Vertex AI."""
    print(f"\nAI Biên kịch đang phân tích ý tưởng: '{y_tuong}'...")

    character_guide = _build_character_guide(character_description)

    # Nếu đang bật chế độ MOCK để test giao diện
    if os.getenv("DEV_FAKE_AI") or os.getenv("MOCK_AI"):
        fake = {
            "tong_so_khung": so_khung,
            "kich_ban": [
                {
                    "khung_so": i + 1,
                    "aspect_ratio": "16:9",
                    "image_size": getattr(CONFIG, 'gemini_image_size', '1024x1024'),
                    "mo_ta_hinh_anh": f"LEFT: Character A on left. RIGHT: Character B on right. Scene {i+1} for idea: {y_tuong}",
                    "sfx": "",
                    "thoai_trai": "...",
                    "thoai_phai": "...",
                }
                for i in range(so_khung)
            ],
        }
        return fake

    prompt_parts: list[str] = []
    prompt_parts.append("Bạn là đạo diễn truyện tranh (Manga/Webtoon) chuyên nghiệp.")
    prompt_parts.append("")
    prompt_parts.append("Ý tưởng gốc của người dùng:")
    prompt_parts.append('"' + str(y_tuong) + '"')
    prompt_parts.append("")
    prompt_parts.append("CHARACTER SET (ưu tiên sử dụng nếu có):")
    prompt_parts.append(character_guide)
    prompt_parts.append("")
    prompt_parts.append("NHIỆM VỤ:")
    prompt_parts.append("1. Tạo chính xác " + str(so_khung) + " khung hình để kể trọn vẹn câu chuyện.")
    prompt_parts.append("2. Chỉ được dùng đúng 2 nhân vật chính xuyên suốt toàn bộ truyện.")
    prompt_parts.append(
        "3. Hai nhân vật chính phải đến từ `CHARACTER SET` ở trên. Nếu `CHARACTER SET` có nhiều hơn 2 nhân vật,"
    )
    prompt_parts.append("   hãy chọn 2 nhân vật chính phù hợp và giữ nguyên tên, vai trò suốt kịch bản.")
    prompt_parts.append("")
    prompt_parts.append("QUY TẮC NHÂN VẬT (bắt buộc):")
    prompt_parts.append("- Tuyệt đối không thay đổi tên nhân vật giữa các khung.")
    prompt_parts.append("- Không được thêm nhân vật chính mới ngoài 2 nhân vật đã chọn.")
    prompt_parts.append(
        "- Mỗi nhân vật phải giữ ổn định: tên, trang phục, màu chủ đạo, đặc điểm ngoại hình và vai trò."
    )
    prompt_parts.append("- Mô tả ngoại hình nên phù hợp người lớn (22–30 tuổi), không dùng phong cách trẻ em/chibi.")
    prompt_parts.append("")
    prompt_parts.append("QUY TẮC KHUNG HÌNH (bắt buộc):")
    prompt_parts.append("- Mỗi khung phải ghi rõ ai ở bên TRÁI và ai ở bên PHẢI.")
    prompt_parts.append("- Hai ô thoại tương ứng với vị trí bên TRÁI và bên PHẢI.")
    prompt_parts.append("   - Luôn điền đầy đủ `thoai_trai` và `thoai_phai`. Nếu một bên im lặng, điền '...'.")
    prompt_parts.append("")
    prompt_parts.append("QUY TẮC MÔ TẢ HÌNH ẢNH (bắt buộc):")
    prompt_parts.append("- Trường `mo_ta_hinh_anh` phải mô tả rõ:")
    prompt_parts.append("    • Nhân vật bên TRÁI (ghi rõ tên) ở đâu, đang làm gì.")
    prompt_parts.append("    • Nhân vật bên PHẢI (ghi rõ tên) ở đâu, đang làm gì.")
    prompt_parts.append("    • Bối cảnh, cảm xúc, hành động chính.")
    prompt_parts.append("- Yêu cầu chính xác hai bóng thoại trong khung.")
    prompt_parts.append("- Không dùng từ khóa mang phong cách trẻ em/chibi như: 'chibi', 'kid', 'child', 'baby-face', 'teen'.")
    prompt_parts.append("")
    prompt_parts.append("QUY TẮC NGÔN NGỮ (bắt buộc):")
    prompt_parts.append("- Trường `thoai_trai`, `thoai_phai` và `sfx` phải là tiếng Việt có dấu đầy đủ.")
    prompt_parts.append("- Tuyệt đối không viết hội thoại theo kiểu không dấu.")
    prompt_parts.append("- Nếu kết quả trả về thiếu dấu hoặc có lỗi chính tả, hãy chỉnh sửa thành tiếng Việt có dấu chuẩn xác.")
    prompt_parts.append("- Sử dụng Unicode (NFC) cho tất cả ký tự tiếng Việt.")
    prompt_parts.append("")
    prompt_parts.append(
        "QUY TẮC TỶ LỆ KHUNG (aspect_ratio): Chọn 1 trong các giá trị sau cho mỗi khung: 1:1, 1:4, 1:8, 2:3, 3:2, 3:4, 4:1, 4:3, 4:5, 5:4, 8:1, 9:16, 16:9"
    )
    prompt_parts.append("")
    prompt_parts.append(
        "QUY TẮC ĐỘ PHÂN GIẢI (image_size): Chọn 1 trong các giá trị sau cho mỗi khung: 512, 1K, 2K"
    )
    prompt_parts.append("")
    prompt_parts.append("FORMAT ĐẦU RA (bắt buộc):")
    prompt_parts.append("- Xuất đúng JSON hợp lệ, không kèm Markdown.")
    prompt_parts.append("- Dùng cấu trúc ví dụ sau:")

    example = {
        "tong_so_khung": so_khung,
        "kich_ban": [
            {
                "khung_so": 1,
                "aspect_ratio": "16:9",
                "image_size": "2K",
                "mo_ta_hinh_anh": "LEFT: ... RIGHT: ...",
                "sfx": "RUT RUT...",
                "thoai_trai": "...",
                "thoai_phai": "...",
            }
        ],
    }

    prompt = "\n".join(prompt_parts) + "\n\n" + json.dumps(example, ensure_ascii=False, indent=4)

    return _writer.generate(prompt)

def get_last_story_error() -> str:
    """Return the latest story generation error message."""
    return getattr(_writer, "last_error", "")