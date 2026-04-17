from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    WEB_PORT: int = 3000
    API_BASE_URL: str = "http://localhost:8000"

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "GovDoc SecureFlow"
    SECRET_KEY: str = "secret"

    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///data/secureflow.db"

    # ── File storage ─────────────────────────────────────────────────────
    LOCAL_FILE_STORAGE_ROOT: str = "data/uploads"
    MAX_UPLOAD_BYTES: int = 15 * 1024 * 1024
    ALLOWED_UPLOAD_MIME_TYPES: List[str] = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ]

    # ── Alibaba Model Studio ─────────────────────────────────────────────
    MODELSTUDIO_API_KEY: str = ""
    MODELSTUDIO_BASE_URL: str = ""
    MODELSTUDIO_DASHSCOPE_URL: str = ""

    # ── Config paths ─────────────────────────────────────────────────────
    MODELS_CONFIG_PATH: str = "api/config/models.yaml"
    ROLES_CONFIG_PATH: str = "api/config/roles.yaml"
    PROMPT_CONFIG_PATH: str = "api/prompts"
    CACHED_AI_STORAGE_ROOT: str = "data/cached_ai"

    # ── Feature toggles ──────────────────────────────────────────────────
    ENABLE_DEMO_MODE: bool = False
    ENABLE_CACHED_AI_RESULTS: bool = False
    ENABLE_LIVE_OCR: bool = True
    ENABLE_LIVE_EMBEDDINGS: bool = True

    # ── Remote deploy ────────────────────────────────────────────────────
    REMOTE_HOST: str = ""
    REMOTE_USER: str = ""
    REMOTE_APP_DIR: str = ""

    # ── Validation helpers ───────────────────────────────────────────────
    def validate_ai_config(self) -> None:
        """Raise ValueError if any Model Studio credential is missing.

        Called only when live AI is needed, NOT at module-import / startup.
        """
        missing: list[str] = []
        if not self.MODELSTUDIO_API_KEY:
            missing.append("MODELSTUDIO_API_KEY")
        if not self.MODELSTUDIO_BASE_URL:
            missing.append("MODELSTUDIO_BASE_URL")
        if not self.MODELSTUDIO_DASHSCOPE_URL:
            missing.append("MODELSTUDIO_DASHSCOPE_URL")
        if missing:
            raise ValueError(f"AI configuration is incomplete – missing: {', '.join(missing)}")

    def validate_remote_config(self) -> None:
        """Raise ValueError if any remote deploy variable is missing."""
        missing: list[str] = []
        if not self.REMOTE_HOST:
            missing.append("REMOTE_HOST")
        if not self.REMOTE_USER:
            missing.append("REMOTE_USER")
        if not self.REMOTE_APP_DIR:
            missing.append("REMOTE_APP_DIR")
        if missing:
            raise ValueError(f"Remote configuration is incomplete – missing: {', '.join(missing)}")

    class Config:
        case_sensitive = True
        env_file = ".env"
        # Ignore unrelated env vars (e.g. frontend VITE_* keys sharing .env)
        extra = "ignore"


settings = Settings()
