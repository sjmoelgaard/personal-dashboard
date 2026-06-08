from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    owner_password: str
    ntfy_url: str = "http://ntfy:80"
    ntfy_topic: str = "mylife"
    anthropic_api_key: str = ""
    ical_url: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "https://mylife.smoelgaard.com/api/admin/google/callback"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
