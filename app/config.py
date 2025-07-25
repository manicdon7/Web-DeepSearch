from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Manages application settings.
    This can be extended with other configurations like database URLs
    or other API keys as your application grows.
    """
    # For now, no specific settings are required for the crawler.
    pass

# Create a single, importable instance of the settings
settings = Settings()
