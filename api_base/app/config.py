"""Application configuration loading and constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import os

from dotenv import load_dotenv
from google.oauth2 import service_account

from .constants.image_options import DEFAULT_IMAGE_SIZE, normalize_image_size


BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)


@dataclass(frozen=True)
class AppConfig:
    """Centralized configuration values loaded from environment variables."""

    base_dir: Path = BASE_DIR
    app_dir: Path = Path(__file__).resolve().parent
    workspace_dir: Path = base_dir / "workspace"
    inputs_dir: Path = workspace_dir / "inputs"
    outputs_dir: Path = workspace_dir / "outputs"
    upload_temp_dir: Path = base_dir / "utils" / "upload_temp"
    download_dir: Path = base_dir / "utils" / "download"
    vector_dir: Path = base_dir / "utils" / "data_vector"
    templates_dir: Path = app_dir / "templates"
    static_dir: Path = app_dir / "static"

    # Vertex AI configuration
    vertex_project_id: str = os.getenv("VERTEX_PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", ""))
    vertex_location: str = os.getenv("VERTEX_LOCATION", "us-central1")
    vertex_text_model: str = os.getenv("VERTEX_TEXT_MODEL", "gemini-1.5-flash")
    vertex_credentials_file: Optional[str] = os.getenv("VERTEX_CREDENTIALS_FILE") or None
    vertex_image_models: List[str] = None

    # Gemini / Google AI Studio API key
    google_ai_api_key: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_AI_API_KEY", ""))
    gemini_image_models: List[str] = None
    gemini_image_size: str = os.getenv("GEMINI_IMAGE_SIZE", DEFAULT_IMAGE_SIZE)
    
    # App logic settings
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_exp_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password_hash: str = os.getenv("ADMIN_PASSWORD_HASH", "")
    password_salt: str = os.getenv("PASSWORD_SALT", "change-me")
    allowed_origins: List[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "vertex_project_id", self.vertex_project_id.strip())
        object.__setattr__(self, "vertex_location", self.vertex_location.strip() or "us-central1")
        object.__setattr__(self, "vertex_text_model", self.vertex_text_model.strip() or "gemini-1.5-flash")
        object.__setattr__(self, "google_ai_api_key", self.google_ai_api_key.strip())
        
        # Helper to parse list from comma-separated env string
        def parse_models(env_var: str, default: str) -> List[str]:
            raw = os.getenv(env_var)
            if raw:
                return [m.strip() for m in raw.split(",") if m.strip()]
            return [default]

        # Set image models dynamically based on .env or default
        object.__setattr__(self, "vertex_image_models", parse_models("VERTEX_IMAGE_MODELS", "imagen-3.0-fast-generate"))
        object.__setattr__(self, "gemini_image_models", parse_models("GEMINI_IMAGE_MODELS", "imagen-3.0-fast-generate"))
        
        object.__setattr__(self, "gemini_image_size", normalize_image_size(self.gemini_image_size))

        if self.allowed_origins is None:
            raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
            object.__setattr__(self, "allowed_origins", [item.strip() for item in raw.split(",") if item.strip()])

        if self.vertex_project_id and not self.vertex_credentials_file and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            try:
                import google.auth
                creds, _proj = google.auth.default()
                if not creds:
                    object.__setattr__(self, "vertex_project_id", "")
            except Exception:
                object.__setattr__(self, "vertex_project_id", "")

    def build_vertex_client_kwargs(self) -> dict:
        kwargs: dict = {"vertexai": True, "project": self.vertex_project_id, "location": self.vertex_location}
        if self.vertex_credentials_file:
            path = Path(self.vertex_credentials_file).expanduser()
            if path.exists():
                kwargs["credentials"] = service_account.Credentials.from_service_account_file(str(path))
        return kwargs

    def build_google_ai_client_kwargs(self) -> dict:
        return {"api_key": self.google_ai_api_key}

CONFIG = AppConfig()