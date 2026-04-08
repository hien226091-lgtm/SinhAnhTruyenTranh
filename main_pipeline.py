import os
import json
import argparse
import time
from PIL import Image

# Import các module của bạn
from modules.ai_generator import tao_anh_truyen_tranh
from modules.text_editor import auto_vietsub


def doc_file_json(duong_dan):
    try:
        with open(duong_dan, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Lỗi khi đọc file {duong_dan}: {e}")
        return None


def chuan_hoa_aspect_ratio(ty_le):
    """
    Đổi format aspect ratio nội bộ như 'aspect_ratio_16_9' -> '16:9'
    để tương thích Gemini image_config.
    """
    mapping = {
        "aspect_ratio_1_1": "1:1",
        "aspect_ratio_16_9": "16:9",
        "aspect_ratio_9_16": "9:16",
        "1:1": "1:1",
        "16:9": "16:9",
        "9:16": "9:16",
    }
    return mapping.get(str(ty_le).strip(), "16:9")


def ghep_thanh_trang_truyen(danh_sach_anh, path_output, so_cot=2, khoang_cach=30, le_trang=30):
    """
    Ghép các khung hình thành 1 trang truyện dạng lưới 2 cột.
    Thứ tự điền khung: trái sang phải, trên xuống dưới.
    Ví dụ: (1,2), (3,4), (5,6).
    """
    print("\nĐang tiến hành ghép các khung thành trang truyện dạng lưới 2 cột...")

    images = []
    for path_anh in danh_sach_anh:
        try:
            img = Image.open(path_anh).convert("RGB")
            images.append(img)
        except Exception as e:
            print(f"Không thể mở ảnh {path_anh}: {e}")

    if not images:
        print("Không có ảnh hợp lệ để ghép trang truyện.")
        return

    widths, heights = zip(*(img.size for img in images))
    rong_o = max(widths)
    cao_o = max(heights)

    so_hang = (len(images) + so_cot - 1) // so_cot

    rong_trang = le_trang * 2 + so_cot * rong_o + (so_cot - 1) * khoang_cach
    cao_trang = le_trang * 2 + so_hang * cao_o + (so_hang - 1) * khoang_cach

    trang_truyen = Image.new('RGB', (rong_trang, cao_trang), color='white')

    for i, img in enumerate(images):
        hang = i // so_cot
        cot = i % so_cot

        x_o = le_trang + cot * (rong_o + khoang_cach)
        y_o = le_trang + hang * (cao_o + khoang_cach)

        x_offset = x_o + int((rong_o - img.width) / 2)
        y_offset = y_o + int((cao_o - img.height) / 2)

        trang_truyen.paste(img, (x_offset, y_offset))

    trang_truyen.save(path_output, quality=95)

    for img in images:
        img.close()
    trang_truyen.close()

    print(f"🎉 HOÀN TẤT TẬP TRUYỆN! File được lưu tại: {path_output}")


def main():
    parser = argparse.ArgumentParser(description="Hệ thống tích hợp sinh truyện tranh AI")
    parser.add_argument("--layout", type=str, required=True, help="Đường dẫn đến file layout.json")
    parser.add_argument("--script", type=str, required=True, help="Đường dẫn đến file script.json")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("KHỞI ĐỘNG HỆ THỐNG PIPELINE - GỘP DỰ ÁN TRUYỆN TRANH AI")
    print("=" * 60)

    data_layout = doc_file_json(args.layout)
    data_script = doc_file_json(args.script)

    if not data_layout or not data_script:
        print("Dừng hệ thống do lỗi đọc dữ liệu đầu vào.")
        return

    thu_muc_out = os.path.join("workspace", "outputs")
    os.makedirs(thu_muc_out, exist_ok=True)
    danh_sach_file_hoan_thanh = []

    so_luong_khung = min(len(data_layout), len(data_script))

    for i in range(so_luong_khung):
        k_so = data_layout[i].get("khung_so", i + 1)
        ty_le_goc = data_layout[i].get("aspect_ratio", "16:9")
        ty_le = chuan_hoa_aspect_ratio(ty_le_goc)

        mo_ta = data_script[i].get("mo_ta_hinh_anh", "")
        # Lấy cứng Trái/Phải
        thoai_trai = data_script[i].get("thoai_trai", "...")
        thoai_phai = data_script[i].get("thoai_phai", "...")
        sfx = data_script[i].get("sfx", "")

        print(f"\n--- Đang xử lý Khung {k_so}/{so_luong_khung} (Tỷ lệ: {ty_le_goc} -> {ty_le}) ---")

        ten_file_raw = f"hinh_{k_so}_raw.jpg"
        ten_file_final = f"hinh_{k_so}.jpg"
        path_raw = os.path.join(thu_muc_out, ten_file_raw)
        path_final = os.path.join(thu_muc_out, ten_file_final)

        prompt_ve = f"Aspect ratio directive: {ty_le}. {mo_ta}"

        # 1. AI VẼ ẢNH RAW
        anh_ve_xong = tao_anh_truyen_tranh(prompt_ve, ten_file_raw, aspect_ratio=ty_le)

        if anh_ve_xong:
            # 2. CHÈN CHỮ VIỆTSUB
            auto_vietsub(anh_ve_xong, path_final, [thoai_trai, thoai_phai], sfx)
            danh_sach_file_hoan_thanh.append(path_final)
        else:
            print(f"❌ Quá trình tạo hình ảnh cho khung {k_so} thất bại.")

        if k_so < so_luong_khung:
            print("Tạm dừng 5 giây tránh Rate Limit của API...")
            time.sleep(5)

    # 3. GHÉP THÀNH TẬP TRUYỆN DẠNG TRANG LƯỚI
    if danh_sach_file_hoan_thanh:
        path_trang_truyen = os.path.join(thu_muc_out, "tap_truyen.jpg")
        ghep_thanh_trang_truyen(danh_sach_file_hoan_thanh, path_trang_truyen, so_cot=2)


if __name__ == "__main__":
    main()