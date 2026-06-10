"""FastAPI application entry point."""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# 1. Các Import chuẩn
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

from .config import CONFIG
from .routers import base, auth, file_upload, comic
from .utils.helpers import ensure_dir
from api_base.app.models.base_db import init_db, get_database_url, create_tables
from api_base.app.models.schema_db import User
from api_base.app.security.admin_deps import verify_admin

# Load .env file
base_dir = Path(__file__).resolve().parent.parent.parent
env_file = base_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)

if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\VoVanHien\AppData\Roaming\gcloud\application_default_credentials.json"

# 2. Khởi tạo FastAPI và Templates toàn cục
app = FastAPI(title="Comic AI API", version="1.0.0")
templates = Jinja2Templates(directory=str(CONFIG.templates_dir))

# 3. Cấu hình App (Middleware & Static)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CONFIG.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(CONFIG.static_dir)), name="static")
app.mount("/outputs", StaticFiles(directory=str(CONFIG.outputs_dir)), name="outputs")

# 4. Các Route định nghĩa trực tiếp vào 'app' (Không nằm trong hàm create_app)
@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/ui")

@app.get("/ui", response_class=HTMLResponse)
def ui(request: Request):
    return templates.TemplateResponse("studio.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

# 5. Khởi tạo Database và Routers
@app.on_event("startup")
def _startup():
    ensure_dir(CONFIG.outputs_dir)
    ensure_dir(CONFIG.upload_temp_dir)
    try:
        init_db()
        if get_database_url():
            create_tables()
    except Exception:
        pass

app.include_router(base.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(file_upload.router, prefix="/api")
app.include_router(comic.router, prefix="/api")