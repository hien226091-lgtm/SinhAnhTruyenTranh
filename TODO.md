## TODO - Chuyển AI sang Gemini API Key (Text + Image)

- [x] 1) Cập nhật `api_base/app/config.py`: giữ `google_ai_api_key` (GEMINI_API_KEY/GOOGLE_AI_API_KEY), giảm phụ thuộc `VERTEX_*` cho text.

- [x] 2) Viết lại `api_base/chatbot/services/story_writer.py`: đổi từ Vertex AI text sang gọi Gemini Text bằng `genai.Client(api_key=...)`.

- [x] 3) Đồng bộ fallback: nếu thiếu `GEMINI_API_KEY` thì trả mock giống hiện tại (để UI không bị block).

- [x] 4) Cập nhật các thông báo lỗi trong `api_base/app/routers/comic.py` (endpoint `/api/comic/phan_tich_kich_ban`) để nhắc đúng Gemini API key.

- [ ] 5) Chạy thử kiểm tra syntax: `python -m py_compile` cho các file đã sửa.
- [ ] 6) Chạy smoke test: gọi local pipeline/mocked (nếu không có key thật) để đảm bảo flow hoạt động.

