import os
from dotenv import load_dotenv
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)


def resolve_backend_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str(BACKEND_DIR / path)


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VECTOR_STORE_PATH = resolve_backend_path(os.getenv("VECTOR_STORE_PATH", "vector_store"))

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing in .env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    OPENAI_API_KEY: str
    
    VECTOR_STORE_PATH: str = VECTOR_STORE_PATH
    
    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    
    # RAG Settings
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 3
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    LLM_MODEL: str = "gpt-4o-mini"
    
    # Authentication
    SECRET_KEY: str = "change-this-to-a-secure-secret-key-min-32-characters"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_EMAIL: str = "admin@example.com"
    
    class Config:
        env_file = str(BACKEND_DIR / ".env")
        case_sensitive = True
        extra = "allow"

settings = Settings()
settings.VECTOR_STORE_PATH = resolve_backend_path(settings.VECTOR_STORE_PATH)
