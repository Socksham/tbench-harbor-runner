from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path

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
    
    # Docker Configuration (for remote Docker daemon)
    # Leave empty to use local Docker socket (/var/run/docker.sock)
    docker_host: Optional[str] = None  # e.g., "tcp://remote-host:2376"
    docker_tls_verify: str = "0"  # "1" for TLS, "0" for no TLS
    docker_cert_path: Optional[str] = None  # Path to TLS certificates if using TLS
    
    # Remote Execution Settings (for running Harbor on remote host)
    remote_execution_enabled: bool = False
    remote_host: Optional[str] = None  # e.g., "ubuntu@ec2-ip-address" or "user@hostname"
    remote_ssh_key_path: Optional[str] = None  # Path to SSH private key (e.g., "~/.ssh/ec2-key.pem")
    remote_work_dir: str = "/tmp/harbor-jobs"  # Working directory on remote host
    remote_python_path: str = "python3"  # Python path on remote host (if needed)
    remote_ssh_port: int = 22  # SSH port (default 22)
    
    @property
    def jobs_dir_absolute(self) -> Path:
        """Get absolute path to jobs directory"""
        return Path(self.jobs_dir).resolve()
    
    @property
    def uploads_dir_absolute(self) -> Path:
        """Get absolute path to uploads directory"""
        return Path(self.uploads_dir).resolve()
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

