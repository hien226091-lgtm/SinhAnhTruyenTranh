"""Google AI Studio-based image generation service."""

from __future__ import annotations

from typing import List, Optional
import base64
from io import BytesIO
from pathlib import Path
import re
import time
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

from api_base.app.config import CONFIG
from api_base.app.constants.image_options import DEFAULT_ASPECT_RATIO, normalize_aspect_ratio, normalize_image_size
from api_base.app.utils.helpers import sanitize_filename

load_dotenv(CONFIG.base_dir / ".env")


def _session_inputs_dir(session_id: str) -> Path:
    """Return inputs directory scoped by session id."""
    safe_session_id = sanitize_filename(session_id)
    return CONFIG.inputs_dir / "sessions" / safe_session_id


def _collect_reference_paths(session_id: str = "default") -> List[Path]:
    """Collect up to 14 reference images for Gemini 3 image models."""
    supported_suffixes = {".png", ".jpg", ".jpeg", ".webp"}
    session_dir = _session_inputs_dir(session_id)

    session_candidates: List[Path] = []
    if session_dir.exists():
        for path in sorted(session_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in supported_suffixes:
                session_candidates.append(path)

    if session_candidates:
        return session_candidates[:14]

    # Backward compatibility for global inputs directory.
    global_candidates: List[Path] = []
    for path in sorted(CONFIG.inputs_dir.iterdir() if CONFIG.inputs_dir.exists() else []):
        if path.is_file() and path.suffix.lower() in supported_suffixes and path.stem.startswith("nhan_vat_"):
            global_candidates.append(path)
    return global_candidates[:14]


def _tai_anh_tham_chieu(session_id: str = "default") -> tuple[List[Image.Image], bool]:
    """Load reference images for Gemini image generation."""
    images: List[Image.Image] = []
    for img_path in _collect_reference_paths(session_id=session_id):
        images.append(Image.open(img_path))
    return images, bool(images)


class GeminiImageGenerator:
    """Encapsulate Google AI Studio image generation requests."""

    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(**CONFIG.build_google_ai_client_kwargs()) if api_key else None
        self.last_error: str = ""

    @staticmethod
    def _is_not_found_error(message: str) -> bool:
        msg = message.upper()
        return "404" in msg or "NOT_FOUND" in msg

    @staticmethod
    def _is_resource_exhausted(message: str) -> bool:
        msg = message.upper()
        return "429" in msg or "RESOURCE_EXHAUSTED" in msg or "QUOTA" in msg

    @staticmethod
    def _is_transient_network_error(message: str) -> bool:
        msg = message.upper()
        transient_markers = [
            "CONNECTION ABORTED",
            "REMOTEDISCONNECTED",
            "MAX RETRIES EXCEEDED",
            "HTTPSCONNECTIONPOOL",
            "FAILED TO RESOLVE",
            "NAME RESOLUTION",
            "GETADDRINFO FAILED",
            "CONNECTION RESET",
            "TIMED OUT",
            "TIMEOUT",
            "TEMPORAR",
        ]
        return any(marker in msg for marker in transient_markers)

    @staticmethod
    def _extract_retry_seconds(message: str) -> float:
        # Matches fragments like: "Please retry in 36.112373087s"
        match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", message, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return 8.0

    @staticmethod
    def _network_backoff_seconds(retry_index: int) -> float:
        # Exponential-ish backoff for flaky DNS/network conditions.
        schedule = [3.0, 6.0, 12.0]
        if retry_index < len(schedule):
            return schedule[retry_index]
        return 18.0

    def generate(
        self,
        contents: list,
        output_path: str,
        aspect_ratio: str,
        image_size: str | None = None,
    ) -> Optional[str]:
        """Generate an image and save it to disk."""
        self.last_error = ""
        if not self._client:
            self.last_error = "Chua cau hinh GEMINI_API_KEY hoac GOOGLE_AI_API_KEY."
            print(f"Loi: {self.last_error}")
            return None

        model_errors: list[str] = []
        normalized_ratio = normalize_aspect_ratio(aspect_ratio)
        preferred_size = normalize_image_size(image_size or CONFIG.gemini_image_size)
        size_attempt_order: list[str] = []
        for candidate in [preferred_size, "2K", "1K", "512"]:
            normalized_candidate = normalize_image_size(candidate)
            if normalized_candidate not in size_attempt_order:
                size_attempt_order.append(normalized_candidate)

        # Quota errors usually mean the current model/size combo is not usable
        # right now. Skip quickly so the generator can fall back to the next
        # size/model instead of waiting for a long retry window.
        max_quota_retries = 0
        max_network_retries = 3

        for model_name in CONFIG.gemini_image_models:
            for image_size in size_attempt_order:

                quota_retry_count = 0
                network_retry_count = 0

                while True:
                    try:
                        config_kwargs = {"response_modalities": ["TEXT", "IMAGE"]}
                        if hasattr(types, "ImageConfig"):
                            config_kwargs["image_config"] = types.ImageConfig(
                                aspect_ratio=normalized_ratio,
                                image_size=image_size,
                            )

                        response = self._client.models.generate_content(
                            model=model_name,
                            contents=contents,
                            config=types.GenerateContentConfig(**config_kwargs),
                        )

                        parts = getattr(response, "parts", None)
                        if not parts and getattr(response, "candidates", None):
                            first = response.candidates[0]
                            if getattr(first, "content", None):
                                parts = getattr(first.content, "parts", None)

                        for part in parts or []:
                            if hasattr(part, "as_image"):
                                image = part.as_image()
                                if image is not None:
                                    image.save(output_path)
                                    return output_path

                            inline_data = getattr(part, "inline_data", None)
                            if inline_data is not None and getattr(inline_data, "data", None):
                                raw = inline_data.data
                                if isinstance(raw, str):
                                    raw = base64.b64decode(raw)
                                img = Image.open(BytesIO(raw))
                                img.save(output_path)
                                img.close()
                                return output_path

                        model_errors.append(
                            f"{model_name} ({image_size}): Khong co du lieu anh trong response"
                        )
                        break
                    except Exception as exc:
                        message = str(exc)

                        if "api key" in message.lower() or "api_key" in message.lower():
                            self.last_error = (
                                "Missing or invalid Google AI Studio API key. Set GEMINI_API_KEY or GOOGLE_AI_API_KEY in api_base/.env."
                            )
                            print(f"Loi trong qua trinh goi Gemini API: {self.last_error}")
                            return None

                        if self._is_not_found_error(message):
                            model_errors.append(
                                f"{model_name} ({image_size}): Model khong ton tai hoac khong ho tro generateContent"
                            )
                            # If model is invalid, skip remaining size attempts for this model.
                            break

                        if self._is_resource_exhausted(message) and quota_retry_count < max_quota_retries:
                            quota_retry_count += 1
                            wait_seconds = min(60.0, self._extract_retry_seconds(message) + 1.0)
                            print(
                                f"Canh bao quota voi {model_name} ({image_size}), doi {wait_seconds:.1f}s de thu lai lan {quota_retry_count}/{max_quota_retries}."
                            )
                            time.sleep(wait_seconds)
                            continue

                        if self._is_transient_network_error(message) and network_retry_count < max_network_retries:
                            wait_seconds = self._network_backoff_seconds(network_retry_count)
                            network_retry_count += 1
                            print(
                                f"Canh bao loi mang tam thoi voi {model_name} ({image_size}), doi {wait_seconds:.1f}s de thu lai lan {network_retry_count}/{max_network_retries}."
                            )
                            time.sleep(wait_seconds)
                            continue

                        model_errors.append(f"{model_name} ({image_size}): {message}")
                        break

        self.last_error = " | ".join(model_errors) if model_errors else "Khong tao duoc anh"
        print(f"Loi trong qua trinh goi Gemini API: {self.last_error}")
        return None


_generator = GeminiImageGenerator(CONFIG.google_ai_api_key)


DEFAULT_CHARACTER_PROMPT = """
- Character 1: Character A (defined by user or reference image).
- Character 2: Character B (defined by user or reference image).
""".strip()

ADULT_CHARACTER_LOCK = """
- All principal characters must appear as fully grown adults (around 22-30 years old).
- Mature anime proportions (about 7.5-8 heads tall), no oversized childlike head/body ratio.
- Strictly avoid child, kid, teen, loli, chibi, baby-face, toddler proportions.
""".strip()


def _build_character_prompt(character_description: str) -> str:
    """Build a stable character profile block for image prompts."""
    cleaned = (character_description or "").strip()
    if cleaned:
        return f"{cleaned}\n{ADULT_CHARACTER_LOCK}"
    return f"{DEFAULT_CHARACTER_PROMPT}\n{ADULT_CHARACTER_LOCK}"


def _normalize_dialogue(text: str) -> str:
    """Normalize dialogue while preserving Vietnamese characters."""
    cleaned = " ".join((text or "").replace("\n", " ").split())
    if not cleaned:
        return "..."
    return cleaned


def get_last_image_error() -> str:
    """Return the last image generation error from Gemini service."""
    return _generator.last_error


def _normalize_output_filename(filename: str) -> str:
    """Normalize output filename to avoid legacy `_raw` artifacts."""
    output = Path(filename)
    stem = output.stem
    if stem.lower().endswith("_raw"):
        clean_stem = stem[:-4] or "hinh_1"
        suffix = output.suffix or ".jpg"
        return str(output.with_name(f"{clean_stem}{suffix}"))
    return filename


def tao_anh_truyen_tranh(
    kich_ban: str,
    ten_file_dau_ra: str = "hinh_1.jpg",
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    image_size: str | None = None,
    character_description: str = "",
    session_id: str = "default",
    thoai_trai: str = "...",
    thoai_phai: str = "...",
    sfx: str = "",
    render_speech: bool = True,
) -> Optional[str]:
    """Generate a comic panel image based on the prompt."""
    ten_file_dau_ra = _normalize_output_filename(ten_file_dau_ra)
    print(f"\nDang goi AI ve anh: '{ten_file_dau_ra}'...")

    output_dir = CONFIG.outputs_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    path_dau_ra = output_dir / ten_file_dau_ra

    image_contents, da_co_anh_ref = _tai_anh_tham_chieu(session_id=session_id)
    if da_co_anh_ref:
        print(f"Da nap {len(image_contents)} anh tham chieu tu inputs.")
    else:
        print("Canh bao: Chua tim thay anh tham chieu trong inputs.")

    character_prompt = _build_character_prompt(character_description)
    left_dialogue = _normalize_dialogue(thoai_trai)
    right_dialogue = _normalize_dialogue(thoai_phai)
    sfx_text = " ".join((sfx or "").replace("\n", " ").split())
    reference_rule = (
        "Use all uploaded reference images as the strongest visual source of truth "
        "for face, outfit, and colors."
        if da_co_anh_ref
        else "No uploaded reference image is available, so rely on the CHARACTER PROFILE strictly."
    )

    prompt = f"""
You are a professional comic art director. Create a high-quality comic panel for the following scenario:

SCENE DESCRIPTION (must follow exactly):
{kich_ban}

CHARACTER PROFILE (source of truth):
{character_prompt}

REFERENCE IMAGE RULE:
{reference_rule}

ART STYLE:
High-quality 2D anime/comic illustration, non-photorealistic. Mature, elegant character design with clean bold black line art, cel-shading, vibrant flat colors, expressive faces, and readable silhouettes. Keep a polished modern webtoon look. Avoid realistic skin texture, realistic lighting, or photographic rendering.

AGE LOCK (must obey):
1. All principal characters must be clearly adult-looking.
2. No childlike facial features and no child body proportions.
3. Do not produce chibi, loli, kid, teen, or toddler style under any circumstance.
4. If any text in SCENE DESCRIPTION suggests "cute/chibi/childlike", keep only the mood and still render adult characters.

CHARACTER CONSISTENCY RULES (crucial):
1. Use exactly 2 principal characters described in CHARACTER PROFILE.
2. Keep character identity stable across the whole comic project: face, hairstyle, outfit, color palette, body shape, and accessories.
3. Do not introduce a new principal character.
4. Respect LEFT/RIGHT assignment written in SCENE DESCRIPTION.
5. Never use the names "Be Trau" or "Be Hai Cau" unless they appear explicitly in CHARACTER PROFILE.

COMPOSITION REQUIREMENTS:
1. A single panel with clean black border.
2. Draw exactly 2 speech bubbles, medium size, white fill, thick black outline.
3. The left bubble is at the top-left corner and must render this exact Vietnamese dialogue: "{left_dialogue}"
4. The right bubble is at the top-right corner and must render this exact Vietnamese dialogue: "{right_dialogue}"
5. Keep Vietnamese diacritics clear and readable. If a sentence is long, wrap to multiple lines but do not change wording.
6. Background must not overlap the bubble interiors.
7. If SFX is provided, render a stylized SFX text in-scene with this exact content: "{sfx_text}". If SFX is empty, do not add any SFX text.
8. Speech text font style must look like clean comic lettering: sans-serif, medium-bold, high contrast black text.
9. Avoid decorative cursive/calligraphy fonts and avoid broken Vietnamese glyphs.
10. Keep letter spacing and line spacing balanced so text is easy to read at a glance.
""".strip()

    # If caller prefers to have speech rendered by us (to guarantee correct Vietnamese diacritics),
    # instruct the model to leave speech bubbles empty so we can overlay clean text later.
    if not render_speech:
        prompt = prompt + "\n\nIMPORTANT: Do NOT render any dialogue text inside the speech bubbles. Leave speech bubbles empty and do not place any readable text. We will overlay the exact dialogue strings later."

    final_contents = [prompt]
    final_contents.extend(image_contents)

    try:
        path = _generator.generate(
            final_contents,
            str(path_dau_ra),
            normalize_aspect_ratio(aspect_ratio),
            normalize_image_size(image_size or CONFIG.gemini_image_size),
        )
        if path:
            print(f"Da hoan tat tao anh: {path}")
            # AI may not render text correctly, so overlay with PIL for guaranteed Vietnamese diacritics
            try:
                from PIL import ImageDraw, ImageFont
                import textwrap
                import os

                img = Image.open(path).convert("RGBA")
                draw = ImageDraw.Draw(img)
                
                # Load font with Vietnamese support
                font = None
                font_size = max(22, img.width // 34)
                font_candidates = [
                    "C:/Windows/Fonts/arial.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/System/Library/Fonts/Helvetica.ttc",
                    "/usr/share/fonts/opentype/liberation/LiberationSans-Regular.otf",
                ]
                
                for font_path in font_candidates:
                    if os.path.exists(font_path):
                        try:
                            font = ImageFont.truetype(font_path, size=font_size)
                            print(f"Using font: {font_path}")
                            break
                        except Exception as e:
                            pass
                
                if font is None:
                    font = ImageFont.load_default()
                    print("Using default font (no Vietnamese support)")

                # Helper to get text size
                def get_text_bbox(text_str, font_obj):
                    try:
                        bbox = font_obj.getbbox(text_str)
                        return (bbox[2] - bbox[0], bbox[3] - bbox[1])
                    except Exception:
                        return (len(text_str) * (font_size // 2), font_size)

                # Prepare dialogues
                left_text = left_dialogue.strip()
                right_text = right_dialogue.strip()

                # Wrap text to fit bubble width ~30% of image width
                char_width, _ = get_text_bbox("A", font)
                wrap_width = max(12, int(img.width * 0.30 / (char_width if char_width > 0 else 12)))
                left_wrapped = textwrap.fill(left_text, width=wrap_width)
                right_wrapped = textwrap.fill(right_text, width=wrap_width)

                # Positions with padding
                padding_x = int(img.width * 0.06)
                padding_y = int(img.height * 0.06)

                # Draw left dialogue (top-left, left-aligned)
                draw.multiline_text(
                    (padding_x, padding_y),
                    left_wrapped,
                    font=font,
                    fill=(0, 0, 0, 255),
                    spacing=2
                )

                # Draw right dialogue (top-right, right-aligned)
                right_lines = right_wrapped.split("\\n")
                line_height = get_text_bbox("Ay", font)[1] + 2
                y_pos = padding_y
                
                for line in right_lines:
                    line_width, _ = get_text_bbox(line, font)
                    x_pos = img.width - padding_x - line_width
                    draw.text(
                        (max(padding_x, x_pos), y_pos),
                        line,
                        font=font,
                        fill=(0, 0, 0, 255)
                    )
                    y_pos += line_height

                # Save with RGB conversion
                img.convert("RGB").save(path, quality=95)
                print(f"Overlayed dialogue: '{left_text}' / '{right_text}'")
            except Exception as e:
                print(f"Warning: PIL overlay failed: {e}")
                import traceback
                traceback.print_exc()
        return path
    finally:
        for im in image_contents:
            try:
                im.close()
            except Exception:
                pass
