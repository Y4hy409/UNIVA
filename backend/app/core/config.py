"""
CLARIUS Backend - Core Configuration Module

This module contains all configuration settings for the CLARIUS platform.
Configuration is loaded from environment variables and provides centralized
access to all application settings.

Architecture Decision:
- Environment-based configuration for flexibility across deployment scenarios
- Pydantic settings for type safety and validation
- Support for offline/on-premises deployment without cloud dependencies
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application Info
    APP_NAME: str = "CLARIUS"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Privacy-Centric, On-Premises AI Business Intelligence Platform"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # Database Configuration
    DB_ENGINE: str = "duckdb" # "duckdb" or "postgres"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/clarius"
    # DuckDB for business data
    DUCKDB_PATH: Path = Path(__file__).resolve().parent.parent.parent / "data" / "clarius.db"
    # ChromaDB for knowledge/documents
    CHROMADB_PATH: Path = Path(__file__).resolve().parent.parent.parent / "data" / "chromadb"
    
    # AI Configuration
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:4b-instruct"
    
    # Security
    SECRET_KEY: str = "change-this-in-production"
    ENCRYPTION_KEY: Optional[str] = None
    
    # Licensing (Offline)
    LICENSE_PATH: Path = Path(__file__).resolve().parent.parent.parent / "config" / "license.lic"
    
    # Feature Flags (Edition-based)
    EDITION: str = "CLARIUS"  # CLARIUS, CLARIUS_COPILOT, UNIVA
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:5174"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency injection for settings."""
    return settings