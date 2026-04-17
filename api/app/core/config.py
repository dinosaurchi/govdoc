from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "GovDoc SecureFlow"
    
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    DATABASE_URL: str = "sqlite:///./data/secureflow.db"
    SECRET_KEY: str = "secret"

    # Stored under repo data/ (see AGENTS.md); container should mount ./data
    LOCAL_FILE_STORAGE_ROOT: str = "./data/uploads"
    MAX_UPLOAD_BYTES: int = 15 * 1024 * 1024
    ALLOWED_UPLOAD_MIME_TYPES: List[str] = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ]
    
    class Config:
        case_sensitive = True

settings = Settings()
