import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()
class Settings(BaseSettings):
    """
    Manages application settings and secrets by loading them from
    environment variables or a .env file.
    """
    # This line tells Pydantic to look for a file named '.env' in the root directory
    # and load its key-value pairs into this class.
    # model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # Pydantic automatically matches this attribute name (huggingface_token)
    # to the environment variable name (HUGGINGFACE_TOKEN) case-insensitively.
    huggingface_token: str = os.getenv("HUGGINGFACE_TOKEN")

# This creates a single, importable instance of your settings.
# When your app starts, this object will be populated with the token from your .env file.
settings = Settings()
