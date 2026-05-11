"""
Application configuration using Pydantic Settings.
Loads environment variables from .env file.
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Gmail OAuth Settings
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_redirect_uri: str = "http://localhost:8000/auth/callback"
    gmail_scopes: List[str] = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.labels",
        "https://www.googleapis.com/auth/userinfo.email",
    ]
    
    # Anthropic Claude API
    anthropic_api_key: str = ""
    claude_model: str = "claude-haiku-4-5-20251001"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./email_guardian.db"
    
    # Security
    secret_key: str = "your-super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    
    # Scheduler Settings
    fetch_interval_minutes: int = 15
    digest_hour: int = 8
    
    # App Settings
    debug: bool = False
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
