"""Gemini (Google AI Studio) based script writing service."""

from __future__ import annotations

import json
import os
from typing import Optional

from google import genai
from google.genai import types

from api_base.app.config import CONFIG


class GeminiStoryWriter:
    """Generate structured story scripts using Gemini Text API (Google AI Studio)."""

    def __init__(self, api_key: str) -> None:
        # Ưu tiên Vertex AI (có billing) nếu đã config VERTEX_PROJECT_ID,
        # fallback sang Google AI Studio API key nếu không có Vertex config.
        if CONFIG.vertex_project_id:
            try:
                self._client = genai.Client(**CONFIG.build_vertex_client_kwargs())
                print(f"[story_writer] Using Vertex AI (project={CONFIG.vertex_project_id}, location={CONFIG.vertex_location})")
            except Exception as exc:
                print(f"[story_writer] Vertex AI init failed ({exc}), falling back to Google AI Studio API key.")
                self._client = genai.Client(**CONFIG.build_google_ai_client_kwargs()) if api_key else None
        elif api_key:
            self._client = genai.Client(**CONFIG.build_google_ai_client_kwargs())
        else:
            self._client = None
        self.last_error: str = ""

    def generate(self, prompt: str) -> Optional[dict]:
        """Generate a story script from the prompt."""
        self.last_error = ""

        if not self._client:
            self.last_error = "Missing GEMINI_API_KEY / GOOGLE_AI_API_KEY (Google AI Studio key)."
            print(f"Loi: {self.last_error}")
            return None

        try:
            response = self._client.models.generate_content(
                model=CONFIG.vertex_text_model,  # dùng model gemini-... theo config (không dùng Vertex project)
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )

            text = getattr(response, "text", None)
            if not text:
                text = str(response)

            try:
                return json.loads(text)
            except Exception:
                # Attempt to extract the first balanced JSON object/array from text
                def _extract_json_fragment(s: str) -> Optional[str]:
                    s = s or ""
                    start_idx = None
                    stack: list[str] = []
                    openers = {"{": "}", "[": "]"}
                    for i, ch in enumerate(s):
                        if start_idx is None and ch in openers:
                            start_idx = i
                            stack.append(openers[ch])
                            continue
                        if start_idx is not None:
                            if ch in openers:
                                stack.append(openers[ch])
                            elif stack and ch == stack[-1]:
                                stack.pop()
                                if not stack:
                                    return s[start_idx : i + 1]
                    return None

                fragment = _extract_json_fragment(text)
                if fragment:
                    try:
                        return json.loads(fragment)
                    except Exception as exc2:
                        self.last_error = f"JSON parse failed: {exc2}"
                        print(self.last_error)
                        print("Response text (truncated):", (text or "")[:2000])
                        return None

                self.last_error = "No valid JSON fragment found in response."
                print(self.last_error)
                print("Response text (truncated):", (text or "")[:2000])
                return None

        except Exception as exc:
            self.last_error = str(exc)
            print("\n=== FULL EXCEPTION DETAILS ===")
            print(f"Exception type: {type(exc).__name__}")
            print(f"Exception message: {self.last_error}")
            print("==============================\n")

            error_lower = self.last_error.lower()

            if "resource_exhausted" in error_lower or "prepayment credits" in error_lower:
                print(
                    "LOI: Gemini credit het. Vui long nap them credit tai "
                    "https://ai.studio/projects hoac chuyen sang dung Vertex AI."
                )
            elif "api key" in error_lower or "api_key" in error_lower:
                print(
                    "Loi tao kich ban: Missing or invalid Google AI Studio API key. "
                    "Set GEMINI_API_KEY or GOOGLE_AI_API_KEY in api_base/.env."
                )

            return None


_writer = GeminiStoryWriter(CONFIG.google_ai_api_key)


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
    """Generate a detailed comic script with panel-level data."""
    print(f"\nAI Bien kich dang phan tich y tuong: '{y_tuong}'...")

    character_guide = _build_character_guide(character_description)

    # Development helper: nếu GEMINI key không có thì trả mock cho UI test.
    if (os.getenv("DEV_FAKE_AI") or os.getenv("MOCK_AI")) and not CONFIG.google_ai_api_key:
        fake = {
            "tong_so_khung": so_khung,
            "kich_ban": [
                {
                    "khung_so": i + 1,
                    "aspect_ratio": "16:9",
                    "image_size": CONFIG.gemini_image_size,
                    "mo_ta_hinh_anh": f"LEFT: Character A on left. RIGHT: Character B on right. Scene {i+1} for idea: {y_tuong}",
                    "sfx": "",
                    "thoai_trai": "...",
                    "thoai_phai": "...",
                }
                for i in range(so_khung)
            ],
        }
        return fake

    # Nếu thiếu GEMINI key thì trả demo mock response để UI không bị block.
    if not CONFIG.google_ai_api_key:
        print("[story_writer] No Gemini API key configured — returning demo mock response.")
        demo = {
            "tong_so_khung": so_khung,
            "kich_ban": [
                {
                    "khung_so": i + 1,
                    "aspect_ratio": "16:9",
                    "image_size": CONFIG.gemini_image_size,
                    "mo_ta_hinh_anh": f"LEFT: Character A on left. RIGHT: Character B on right. Demo scene {i+1} for idea: {y_tuong}",
                    "sfx": "",
                    "thoai_trai": "...",
                    "thoai_phai": "...",
                }
                for i in range(so_khung)
            ],
        }
        return demo

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
        "QUY TẮC TỶ LỆ KHUNG (aspect_ratio): Chọn 1 trong các giá trị sau cho mỗi khung: 1:1, 1:4, 1:8, 2:3, 3:2, 3:4, 4:1, 4:3, 4:5, 5:4, 8:1, 9:16, 16:9, 21:9"
    )
    prompt_parts.append("")
    prompt_parts.append(
        "QUY TẮC ĐỘ PHÂN GIẢI (image_size): Chọn 1 trong các giá trị sau cho mỗi khung: 512, 1K, 2K, 4K"
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
