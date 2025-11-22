from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    api_title: str = "Terminal-Bench Harbor Runner API"
    api_version: str = "1.0.0"
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tbench"
    
    # Redis (for Celery)
    redis_url: str = "redis://localhost:6379/0"
    
    # OpenRouter
    default_openrouter_key: Optional[str] = None
    
    # File Storage
    uploads_dir: str = "uploads"
    jobs_dir: str = "jobs"
    
    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Harbor Settings
    harbor_timeout_multiplier: float = 1.0
    max_concurrent_runs_per_worker: int = 1
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

