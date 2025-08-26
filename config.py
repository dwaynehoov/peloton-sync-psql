"""Configuration management for the Peloton Data Sync application."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""
    
    model_config = SettingsConfigDict(env_prefix="DB_")
    
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="peloton_data", description="Database name")
    user: str = Field(description="Database username")
    password: str = Field(description="Database password")
    
    @property
    def url(self) -> str:
        """Generate database URL from components."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class PelotonConfig(BaseSettings):
    """Peloton API configuration settings."""
    
    model_config = SettingsConfigDict(env_prefix="PELOTON_")
    
    username: str = Field(description="Peloton username or email")
    password: str = Field(description="Peloton password")
    base_url: str = Field(default="https://api.onepeloton.com", description="Peloton API base URL")


class AppConfig(BaseSettings):
    """Application configuration settings."""
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    
    # API Client
    max_retries: int = Field(default=3, description="Maximum API retry attempts")
    retry_delay: int = Field(default=1, description="Delay between retries in seconds")
    rate_limit_calls: int = Field(default=60, description="Rate limit calls per period")
    rate_limit_period: int = Field(default=60, description="Rate limit period in seconds")
    
    # Data Sync
    sync_interval_hours: int = Field(default=24, description="Hours between sync operations")
    max_workouts_per_sync: int = Field(default=100, description="Maximum workouts to sync per run")
    include_performance_data: bool = Field(default=True, description="Include performance metrics")
    include_heart_rate_data: bool = Field(default=True, description="Include heart rate data")
    
    # Database URL override
    database_url: Optional[str] = Field(default=None, description="Complete database URL")


def get_config() -> tuple[AppConfig, DatabaseConfig, PelotonConfig]:
    """Get all configuration objects."""
    app_config = AppConfig()
    db_config = DatabaseConfig()
    peloton_config = PelotonConfig()
    
    return app_config, db_config, peloton_config


def get_database_url() -> str:
    """Get the database URL from configuration."""
    app_config, db_config, _ = get_config()
    
    if app_config.database_url:
        return app_config.database_url
    
    return db_config.url
