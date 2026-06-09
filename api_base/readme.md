# Comic AI API

## Tong quan
Du an cung cap FastAPI backend cho viec phan tich kich ban va san xuat truyen tranh AI.

## Cau truc
```
api_base/
  app/
    main.py
    config.py
    models/
    routers/
    security/
    utils/
    templates/
    static/
  chatbot/
    services/
    utils/
  ingestion/
  utils/
    download/
    upload_temp/
    data_vector/
  workspace/
    inputs/
    outputs/
  start.sh
  requirements.txt
```

## Thiet lap nhanh
1. Tao file .env (xem mau ben duoi).
2. Cai dat dependency:
   ```bash
   pip install -r requirements.txt
   ```
3. Chay API:
   ```bash
  python ..\run_api_root.py
   ```

## Vi du .env
```
VERTEX_PROJECT_ID=your-gcp-project-id
VERTEX_LOCATION=us-central1
VERTEX_TEXT_MODEL=gemini-2.5-flash
VERTEX_CREDENTIALS_FILE=C:\\path\\to\\service-account.json
GEMINI_API_KEY=your-google-ai-studio-api-key
GEMINI_IMAGE_MODELS=gemini-2.5-flash-image
JWT_SECRET=change-me
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=hash_here
PASSWORD_SALT=change-me
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Luu y: phan sinh anh dung Google AI Studio/Gemini API key qua `GEMINI_API_KEY` hoac `GOOGLE_AI_API_KEY`. Cac bien Vertex AI chi can neu ban van dung luong viet kich ban bang Vertex.

## Khoi tao mat khau admin
Su dung ham `hash_password` trong `app/security/security.py` de tao hash va luu vao `ADMIN_PASSWORD_HASH`.

## API chinh
- `GET /api/health`
- `POST /api/auth/login`
- `POST /api/comic/phan_tich_kich_ban`
- `POST /api/comic/san_xuat`
- `POST /api/files/upload`
- `GET /api/files/{filename}`

## Dau ra khi san xuat
- Anh ket qua duoc dat theo thu tu: `Anh_1.jpg`, `Anh_2.jpg`, ...
- File `workspace/outputs/anh_manifest.json` ghi ro anh nao ung voi ty le khung nao.
