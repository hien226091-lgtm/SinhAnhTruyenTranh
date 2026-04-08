from flask import Flask, render_template, request, jsonify
import os
import time
from modules.ai_generator import ve_truyen_gemini
from modules.text_editor import auto_vietsub
# Import thêm Tổ Biên Kịch
from modules.story_writer import viet_kich_ban_chi_tiet
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__, static_folder='workspace/outputs', static_url_path='/outputs')

@app.route('/')
def home():
    return render_template('index.html')

# ==========================================
# API MỚI: PHÂN TÍCH KỊCH BẢN TỪ FILE TXT
# ==========================================
@app.route('/api/phan_tich_kich_ban', methods=['POST'])
def phan_tich_kich_ban():
    data = request.json
    y_tuong_tho = data.get('text', '')
    
    if not y_tuong_tho:
        return jsonify({"success": False, "message": "Nội dung trống!"})

    print("\n✍️ Web đang gọi Tổ Biên Kịch phân tích file tải lên...")
    
    # Gọi AI đọc ý tưởng thô và chia thành 4 khung chuẩn xác
    kich_ban_json = viet_kich_ban_chi_tiet(y_tuong_tho, so_khung=4)
    
    if kich_ban_json:
        return jsonify({"success": True, "data": kich_ban_json})
    else:
        return jsonify({"success": False, "message": "AI phân tích thất bại."})

# ==========================================
# API CŨ: SẢN XUẤT TRUYỆN TRANH
# ==========================================
@app.route('/api/san_xuat', methods=['POST'])
def san_xuat_api():
    data = request.json
    panels = data.get('panels', [])
    
    thu_muc_dau_ra = os.path.join("workspace", "outputs")
    os.makedirs(thu_muc_dau_ra, exist_ok=True)
    
    danh_sach_anh_thanh_pham = []
    
    for idx, panel in enumerate(panels):
        khung_so = idx + 1
        prompt_ve = panel["mo_ta"]
        thoai_raw = panel["thoai"]
        
        danh_sach_thoai = [t.strip() for t in thoai_raw.split('\n') if t.strip()]
        
        ten_file_goc = f"web_panel_{khung_so}_raw.jpg"
        ten_file_vietsub = f"web_panel_{khung_so}_vietsub.jpg"
        path_vietsub_full = os.path.join(thu_muc_dau_ra, ten_file_vietsub)
        
        print(f"\n🎬 Đang xử lý Khung {khung_so} từ Web...")
        
        path_raw = tao_anh_truyen_tranh(prompt_ve, ten_file_goc)
        
        if path_raw:
            thoai_trai = danh_sach_thoai[0] if len(danh_sach_thoai) > 0 else "..."
            thoai_phai = danh_sach_thoai[1] if len(danh_sach_thoai) > 1 else "..."
            sfx = panel.get("sfx", "")
            auto_vietsub(path_raw, path_vietsub_full, thoai_trai, thoai_phai, sfx)
            danh_sach_anh_thanh_pham.append(f"/outputs/{ten_file_vietsub}")
        else:
            print(f"❌ Lỗi vẽ khung {khung_so}")
            
        if khung_so < len(panels):
            time.sleep(8)
            
    return jsonify({"success": True, "images": danh_sach_anh_thanh_pham})

if __name__ == '__main__':
    print("\n🚀 TRẠM CHỈ HUY WEB ĐÃ KHỞI ĐỘNG!")
    print("👉 Mở trình duyệt và truy cập: http://127.0.0.1:5000\n")
    app.run(debug=True, port=5000)