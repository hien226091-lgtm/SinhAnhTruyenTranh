import os

# Danh sách các phòng ban cần xây
thu_muc = ['modules', 'templates', 'static', 'workspace/inputs', 'workspace/outputs']
# Danh sách các file rỗng cần tạo
tap_tin = [
    'app.py', '.env', 
    'modules/ai_generator.py', 'modules/text_editor.py', 
    'templates/index.html', 'static/style.css'
]

print("🚀 Đang khởi công xây dựng Xưởng Studio...")
for tm in thu_muc:
    os.makedirs(tm, exist_ok=True)
    print(f"📁 Đã tạo thư mục: {tm}")

for tt in tap_tin:
    with open(tt, 'a', encoding='utf-8') as f:
        pass # Chỉ tạo file rỗng
    print(f"📄 Đã tạo file: {tt}")

print("✅ Hoàn tất! Dự án của bạn đã sẵn sàng.")