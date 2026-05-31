from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    owner_password: str
    ntfy_url: str = "http://ntfy:80"
    ntfy_topic: str = "mylife"
    anthropic_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
