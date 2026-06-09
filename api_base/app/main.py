"""FastAPI application entry point."""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file FIRST before importing anything else
base_dir = Path(__file__).resolve().parent.parent.parent
env_file = base_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Set credentials if not already set
if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\VoVanHien\AppData\Roaming\gcloud\application_default_credentials.json"

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse

from .config import CONFIG
from .routers import base, auth, file_upload, comic
from .utils.helpers import ensure_dir
from api_base.app.models.base_db import init_db, get_database_url, create_tables


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    ensure_dir(CONFIG.outputs_dir)
    ensure_dir(CONFIG.upload_temp_dir)

    app = FastAPI(title="Comic AI API", version="1.0.0")

    # Initialize DB engine if DATABASE_URL is configured.
    try:
        init_db()
    except Exception:
        # ignore DB init failures here; endpoints can handle missing DB
        pass

    @app.on_event("startup")
    def _startup_init_db() -> None:
        # If a DATABASE_URL is present attempt to create tables automatically.
        try:
            if get_database_url():
                create_tables()
        except Exception:
            # Don't crash the app on table-creation errors -- warn via logs if desired.
            pass

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CONFIG.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory=str(CONFIG.static_dir)), name="static")
    app.mount("/outputs", StaticFiles(directory=str(CONFIG.outputs_dir)), name="outputs")

    templates = Jinja2Templates(directory=str(CONFIG.templates_dir))

    @app.get("/")
    def root():
        """Redirect to the web UI."""
        return RedirectResponse(url="/ui")

    @app.get("/ui")
    def ui(request: Request):
        """Serve the web UI page."""
        # Serve the new Studio UI by default. Keep index.html available at /index.html if needed.
        return templates.TemplateResponse("studio.html", {"request": request})

    @app.get("/login.html")
    def login_page(request: Request):
        """Serve the login page."""
        return templates.TemplateResponse("login.html", {"request": request})

    @app.get("/register.html")
    def register_page(request: Request):
        """Serve the register page."""
        return templates.TemplateResponse("register.html", {"request": request})

    @app.get("/studio.html")
    def studio_page(request: Request):
        """Serve the studio UI page."""
        return templates.TemplateResponse("studio.html", {"request": request})

    app.include_router(base.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(file_upload.router, prefix="/api")
    app.include_router(comic.router, prefix="/api")

    return app


app = create_app()
