import os
import secrets
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "Urban Scenery Ventures - Electronics Store API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL") or "sqlite:///./urban_ventures.db"
    if DATABASE_URL == "None" or not DATABASE_URL.strip():
        DATABASE_URL = "sqlite:///./urban_ventures.db"
        
    # Security
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").strip().lower()
    SECRET_KEY: str = os.getenv("SECRET_KEY", "").strip()
    if not SECRET_KEY:
        if ENVIRONMENT in {"production", "prod"}:
            raise RuntimeError("SECRET_KEY must be configured in production.")
        SECRET_KEY = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # CORS
    _cors_origins = os.getenv("CORS_ORIGINS", "")
    CORS_ORIGINS: List[str] = (
        [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]
        if _cors_origins.strip()
        else [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    )


settings = Settings()
