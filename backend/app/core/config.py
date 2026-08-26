from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables (or a .env file)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://transitsync:transitsync@localhost:5432/transitsync"
    mbta_api_base_url: str = "https://api-v3.mbta.com"
    mbta_api_key: str = ""


settings = Settings()
