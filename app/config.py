"""Configuration settings for the CPCC Enrollment API."""

import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment
    environment: str = "development"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    api_base_url: Optional[str] = None
    
    # CPCC Configuration
    cpcc_base_url: str = "https://mycollegess.cpcc.edu"
    cpcc_search_endpoint: str = "/Student/Courses/PostSearchCriteria"
    cpcc_sections_endpoint: str = "/Student/Courses/Sections"
    cpcc_timeout_seconds: int = 30
    request_timeout_seconds: int = 30
    
    # Caching Configuration
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300  # 5 minutes
    session_ttl_seconds: int = 1800  # 30 minutes
    
    # API Configuration
    max_concurrent_requests: int = 10
    max_subjects_per_request: int = 10
    allowed_origins: list = ["*"]
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Development Settings
    debug: bool = False
    reload: bool = False
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level is one of the standard levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v):
        """Validate log format is supported."""
        valid_formats = ["json", "text"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Log format must be one of: {valid_formats}")
        return v.lower()
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False
    }


# Global settings instance
settings = Settings()