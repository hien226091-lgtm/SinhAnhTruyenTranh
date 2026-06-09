import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY) if API_KEY and API_KEY != "xxx" else None


def viet_kich_ban_chi_tiet(y_tuong, so_khung=6):
    print(f"\n🧠 AI Biên Kịch đang phân tích ý tưởng: '{y_tuong}'...")

    prompt = f"""
Bạn là Đạo diễn truyện tranh Manga/Webtoon thiên tài.

Ý tưởng gốc của người dùng:
"{y_tuong}"

NHIỆM VỤ:
1. Tạo chính xác {so_khung} khung hình để kể trọn vẹn câu chuyện.
2. Chỉ được dùng đúng 2 nhân vật xuyên suốt toàn bộ truyện:
   - Bé Trâu: em bé/chibi mặc đồ con trâu hoặc bò, có sừng nhỏ.
   - Bé Hải Cẩu: em bé/chibi mặc đồ hải cẩu, có vây/chân chèo đặc trưng.
3. Hai nhân vật này phải giữ nguyên danh tính từ đầu đến cuối. Không tạo thêm nhân vật phụ, người qua đường, ba mẹ, bạn bè, nhân viên, động vật khác có vai trò nhân vật.
4. Mọi khung phải phù hợp để phần vẽ ảnh phía sau dùng ảnh tham chiếu nhân vật Bé Trâu và Bé Hải Cẩu.

QUY TẮC KỂ CHUYỆN:
- Ưu tiên chuyện đời thường dễ thương, hài hước, ấm áp, dễ hiểu với trẻ em.
- Phải có mở đầu, diễn biến, cao trào nhẹ, và kết thúc đáng yêu.
- Mỗi khung phải có hành động cụ thể, thay đổi góc nhìn hoặc diễn biến, tránh lặp lại.
- Nếu ý tưởng liên quan đi chơi/nghỉ dưỡng/ngoài trời, có thể tận dụng bối cảnh biển, resort, hồ bơi, nhà hàng, hoàng hôn.

QUY TẮC KHÔNG GIAN BẮT BUỘC:
- Mỗi khung phải ghi cực rõ ai ở bên TRÁI, ai ở bên PHẢI.
- Hai ô thoại luôn tương ứng với vị trí bên trái và bên phải.
- Luôn điền đủ "thoai_trai" và "thoai_phai". Nếu một bên im lặng, ghi đúng chuỗi "...".
- Không để trống bất kỳ trường nào.

QUY TẮC MÔ TẢ HÌNH ẢNH BẮT BUỘC:
- Trường "mo_ta_hinh_anh" phải mô tả rõ:
  + Bé Trâu ở đâu, làm gì.
  + Bé Hải Cẩu ở đâu, làm gì.
  + Bối cảnh, cảm xúc, hành động chính.
- Phải nhắc rõ đây là một comic panel sạch sẽ.
- Phải yêu cầu chính xác hai bóng thoại trong khung.
- Không mô tả thêm hộp thoại phụ, caption box, thought bubble, hay bong bóng thứ 3.

QUY TẮC TỶ LỆ KHUNG (aspect_ratio):
- Chọn 1 trong các giá trị sau cho mỗi khung:
  "aspect_ratio_1_1"
  "aspect_ratio_16_9"
  "aspect_ratio_9_16"
- Hãy phối hợp đa dạng, không dùng duy nhất một tỷ lệ cho toàn bộ truyện.

YÊU CẦU NỘI DUNG THOẠI:
- Lời thoại ngắn, tự nhiên, đúng giọng trẻ em.
- Phù hợp với hành động của từng nhân vật.
- Không dùng lời dẫn truyện trong ô thoại.
- Không lặp nguyên câu giữa nhiều khung nếu không cần thiết.

FORMAT ĐẦU RA BẮT BUỘC:
- Chỉ xuất JSON hợp lệ.
- Không Markdown.
- Không giải thích thêm.
- Phải đúng cấu trúc sau:

{{
    "tong_so_khung": {so_khung},
    "kich_ban": [
        {{
            "khung_so": 1,
            "aspect_ratio": "aspect_ratio_16_9",
            "mo_ta_hinh_anh": "LEFT: Bé Trâu ... RIGHT: Bé Hải Cẩu ... cute manga comic panel, clean black panel border, exactly 2 empty speech bubbles, one large white bubble with thick black outline at top-left and one large white bubble with thick black outline at top-right, bubble interiors kept clean and unobstructed.",
            "sfx": "RỘT RỘT...",
            "thoai_trai": "Câu nói của nhân vật bên trái",
            "thoai_phai": "Câu nói của nhân vật bên phải"
        }}
    ]
}}
""".strip()

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ Lỗi tạo kịch bản: {e}")
        return None
