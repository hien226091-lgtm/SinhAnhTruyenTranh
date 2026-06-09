from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api_base"))

from api_base.chatbot.services.ai_generator import tao_anh_truyen_tranh
from api_base.app.config import CONFIG

def main():
    print("Outputs dir:", CONFIG.outputs_dir)
    path = tao_anh_truyen_tranh(
        kich_ban=(
            "LEFT: Nhan vat 1: ngoi ben trai, bat ngo ngoai tinh; "
            "RIGHT: Nhan vat 2: o ben phai, gian du, doi tien. BACKGROUND: van phong voi binh nuoc."
        ),
        ten_file_dau_ra="demo_test_1.jpg",
        aspect_ratio="16:9",
        image_size="4K",
        character_description=(
            "Nhan vat 1: Màu toc trang, ao ngụ, giong de thuong.\n"
            "Nhan vat 2: Bọc bò, ao den, bieu cam nghiem tuc."
        ),
        session_id="default",
        thoai_trai="À ha... quên mất...",
        thoai_phai="Trả tiền đi rồi nói chuyện khỏi ngứa tiết.",
        sfx="",
        render_speech=True,
    )
    print("Generated image path:", path)

if __name__ == '__main__':
    main()
