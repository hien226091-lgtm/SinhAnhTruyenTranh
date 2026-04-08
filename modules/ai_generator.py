import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

# Tải biến môi trường
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY) if API_KEY and API_KEY != "xxx" else None


def _tai_anh_tham_chieu():
    """
    Tải 2 ảnh nhân vật tham chiếu từ workspace/inputs để giữ đúng nhân vật.
    Trả về:
    - danh_sach_anh: list PIL.Image
    - duong_dan_da_tim_thay: True nếu đủ 2 ảnh, False nếu thiếu
    """
    img_path_1 = os.path.join("workspace", "inputs", "nhan_vat_1.png")
    img_path_2 = os.path.join("workspace", "inputs", "nhan_vat_2.png")

    if os.path.exists(img_path_1) and os.path.exists(img_path_2):
        img1 = Image.open(img_path_1)
        img2 = Image.open(img_path_2)
        return [img1, img2], True

    return [], False


def tao_anh_truyen_tranh(kich_ban: str, ten_file_dau_ra: str = "hinh_1_raw.jpg", aspect_ratio: str = "1:1") -> str:
    print(f"\n🎨 Đang gọi AI vẽ ảnh: '{ten_file_dau_ra}'...")
    if not client:
        print("Lỗi: Chưa cấu hình API Key.")
        return None

    thu_muc_out = os.path.join("workspace", "outputs")
    os.makedirs(thu_muc_out, exist_ok=True)
    path_dau_ra = os.path.join(thu_muc_out, ten_file_dau_ra)

    image_contents, da_co_anh_ref = _tai_anh_tham_chieu()
    if da_co_anh_ref:
        print("✓ Đã nạp ảnh tham chiếu nhân vật từ workspace/inputs.")
    else:
        print("⚠ Không tìm thấy đủ 2 ảnh tham chiếu tại workspace/inputs/nhan_vat_1.png và nhan_vat_2.png")

    # Prompt tối ưu để AI luôn dùng đúng 2 nhân vật và chừa đúng 2 bóng thoại trống
    prompt = f"""
You are a professional comic art director creating ONE polished comic panel.

SCENARIO:
{kich_ban}

VERY IMPORTANT CHARACTER LOCK:
- This panel must contain ONLY these two recurring characters.
- Character 1 = Bé Trâu = the child in the COW onesie with small horns, based on reference image 1.
- Character 2 = Bé Hải Cẩu = the child in the SEAL onesie with flippers/fins, based on reference image 2.
- Keep their costume, face type, proportions, and identity consistent with the reference images.
- Do not replace them with other children, animals, adults, or extra side characters.
- Do not merge the two characters into one.
- If only one character is active in the scene, the other can still appear nearby, but the cast must remain exactly these two characters.

ART STYLE:
- Cute Vietnamese children's comic / manga chibi style.
- Clean black line art, bright flat colors, high clarity, expressive faces.
- Professional comic panel composition.
- Single panel only.
- Clear black panel border.

LAYOUT AND SPEECH BUBBLE REQUIREMENTS:
- Draw EXACTLY 2 large empty speech bubbles only.
- Bubble 1 must be near the top-left corner.
- Bubble 2 must be near the top-right corner.
- Both bubbles must be pure white inside, with thick black outline, comic style.
- Keep both bubbles completely empty: no text, no symbols, no punctuation, no watermark inside.
- The background and all characters must stay below or away from the bubble interiors.
- Do not let objects, hair, hands, decorations, or scenery overlap inside the white bubble area.
- The two bubbles should be clean, readable, balanced, and similar to a printed children's comic sample.
- Do not create any extra caption box, narration box, or extra speech bubble.

COMPOSITION:
- Bé Trâu and Bé Hải Cẩu must be clearly visible and easy to distinguish.
- Their expressions and body language should strongly match the scenario.
- Background should support the story, but must never compete with or cover the two speech bubbles.
- Make the result look like a finished comic panel ready for later dialogue insertion.
""".strip()

    final_contents = [prompt]
    final_contents.extend(image_contents)

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=final_contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio, image_size="1K")
            )
        )

        for part in response.parts:
            if image := part.as_image():
                image.save(path_dau_ra)
                print(f"✓ Hoàn tất tạo ảnh raw: {path_dau_ra}")
                return path_dau_ra

    except Exception as e:
        print("Lỗi trong quá trình gọi Gemini API:", e)
        return None
    finally:
        for im in image_contents:
            try:
                im.close()
            except Exception:
                pass

    return None


if __name__ == "__main__":
    y_tuong_mau = "Bé Trâu và Bé Hải Cẩu đi dạo ở resort ven biển lúc hoàng hôn, vừa ngắm cảnh vừa trò chuyện vui vẻ."
    tao_anh_truyen_tranh(y_tuong_mau)