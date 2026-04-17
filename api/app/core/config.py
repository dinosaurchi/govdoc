from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "GovDoc SecureFlow"
    
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    DATABASE_URL: str = "sqlite:///./data/secureflow.db"
    SECRET_KEY: str = "secret"
    
    class Config:
        case_sensitive = True

settings = Settings()
