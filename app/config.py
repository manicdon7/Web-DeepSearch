import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

load_dotenv()

class OptimizationSettings(BaseSettings):
    """Configuration for search optimization parameters"""
    
    # Concurrent scraping settings
    max_concurrent_scrapers: int = 5
    scraper_timeout_seconds: int = 10
    max_sources_to_scrape: int = 15
    
    # Caching settings
    cache_ttl_seconds: int = 3600
    enable_caching: bool = True
    
    # Performance monitoring
    enable_performance_monitoring: bool = True
    log_level: str = "INFO"
    
    # Circuit breaker settings
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60
    
    # Summary generation settings
    default_summary_length: int = 300
    max_summary_length: int = 800
    min_summary_length: int = 100
    
    # Content quality thresholds
    min_content_quality_score: float = 0.3
    min_relevance_score: float = 0.4
    
    class Config:
        env_prefix = "OPTIMIZATION_"

class Settings(BaseSettings):
    """
    Manages application settings and secrets by loading them from
    environment variables or a .env file.
    """

    # Pydantic automatically matches this attribute name (huggingface_token)
    # to the environment variable name (HUGGINGFACE_TOKEN) case-insensitively.
    huggingface_token: Optional[str] = os.getenv("HUGGINGFACE_TOKEN", "test-token")
    
    # Optimization settings
    optimization: OptimizationSettings = OptimizationSettings()

# This creates a single, importable instance of your settings.
# When your app starts, this object will be populated with the token from your .env file.
settings = Settings()
