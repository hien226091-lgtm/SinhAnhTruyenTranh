import os
import time
from modules.story_writer import viet_kich_ban_chi_tiet
from modules.ai_generator import tao_anh_truyen_tranh
from modules.text_editor import auto_vietsub

def san_xuat_truyen_dai_tap(y_tuong, so_khung=4):
    print("\n" + "★" * 60)
    print(f"🎬 XƯỞNG STUDIO AI BẤM MÁY: TRUYỆN DÀI TẬP ({so_khung} KHUNG)")
    print("★" * 60)

    # 1. Gọi Tổ Biên Kịch lên kịch bản
    kich_ban_chi_tiet = viet_kich_ban_chi_tiet(y_tuong, so_khung)
    if not kich_ban_chi_tiet:
        print("❌ Nghỉ quay! Biên kịch không nộp kịch bản.")
        return

    thu_muc_dau_ra = os.path.join("workspace", "outputs")
    os.makedirs(thu_muc_dau_ra, exist_ok=True)

    # 2. Vòng lặp Sản xuất: Lần lượt quay từng cảnh một
    for panel in kich_ban_chi_tiet["kich_ban"]:
        khung_so = panel["khung_so"]
        prompt_ve = panel["mo_ta_hinh_anh"]
        thoai_trai = panel.get("thoai_trai", "...")
        thoai_phai = panel.get("thoai_phai", "...")
        sfx = panel.get("sfx", "")
        
        print("\n" + "-" * 50)
        print(f"🎥 ĐANG QUAY CẢNH {khung_so}/{len(kich_ban_chi_tiet['kich_ban'])}...")
        print("-" * 50)
        
        ten_file_goc = f"panel_{khung_so}_raw.jpg"
        ten_file_vietsub = f"panel_{khung_so}_vietsub.jpg"
        
        # 2.1 Gọi Họa sĩ Gemini vẽ tranh (bóng thoại trống) dựa trên mô tả tiếng Anh
        path_raw = tao_anh_truyen_tranh(prompt_ve, ten_file_goc)
        
        if path_raw:
            # 2.2 Gọi Tổ Hậu Kỳ (OpenCV) chèn chữ tiếng Việt
            path_vietsub = os.path.join(thu_muc_dau_ra, ten_file_vietsub)
            auto_vietsub(path_raw, path_vietsub, thoai_trai, thoai_phai, sfx)
            print(f"✅ Đã xuất xưởng thành công Khung {khung_so}!")
        else:
            print(f"❌ Khung {khung_so} bị hỏng, bỏ qua.")
            
        # ⏳ NGHỈ GIẢI LAO TRƯỚC KHI QUAY CẢNH TIẾP THEO
        # Cực kỳ quan trọng: Nghỉ 8 giây để Google không khóa tài khoản vì spam API quá nhanh
        if khung_so < so_khung:
            print("⏳ Cho tổ quay phim nghỉ 8 giây uống nước để tránh lỗi hệ thống Google...")
            time.sleep(8)

    print("\n" + "🎉" * 20)
    print("🍿 CHÚC MỪNG SẾP! TOÀN BỘ TẬP TRUYỆN ĐÃ XUẤT XƯỞNG!")
    print(f"📂 Mời sếp mở thư mục: {thu_muc_dau_ra} để xem 4 bức tranh thành phẩm.")
    print("🎉" * 20 + "\n")

# ==========================================
# GÓC SÁNG TÁC DÀNH CHO BẠN (GIÁM ĐỐC)
# ==========================================
if __name__ == "__main__":
    
    # Bạn chỉ cần gõ 1 dòng ý tưởng duy nhất vào đây
    y_tuong_moi = "Bé Trâu lỡ tay làm đổ ly cà phê lên tập tài liệu mật. Bé Hải Cẩu vội vàng lấy máy sấy tóc ra sấy nhưng lỡ bật nấc mạnh nhất làm giấy bay tung tóe khắp phòng."
    
    # Bấm nút sản xuất một lèo 4 khung truyện!
    san_xuat_truyen_dai_tap(y_tuong_moi, so_khung=4)
