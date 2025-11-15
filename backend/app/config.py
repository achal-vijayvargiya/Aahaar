"""
Configuration settings for the application.
"""
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "DrAssistent API"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/drassistent"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OpenRouter AI Configuration
    OPENROUTER_API_KEY: str = "sk-or-v1-placeholder-get-from-openrouter-ai"
    DIET_PLAN_MODEL: str = "anthropic/claude-3.5-sonnet"  # or "meta-llama/llama-3.1-70b-instruct"
    DIET_PLAN_TEMPERATURE: float = 0.7
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        str_strip_whitespace=True,
        validate_default=True,
        env_file_encoding='utf-8'
    )


settings = Settings()

# CORS Origins - separate constant (not part of Settings to avoid .env parsing issues)
BACKEND_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://localhost:8081"
]

