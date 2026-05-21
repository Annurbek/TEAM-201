from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Student Ranking System"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "edumetrik"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DATABASE_URL_OVERRIDE: str | None = None
    SQL_ECHO: bool = False
    UPLOAD_DIR: str = "./uploads"
    CORS_ORIGINS: str = "*"

    SECRET_KEY: str = Field(default="change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        return "sqlite+aiosqlite:///./data/edumetrik.db"


settings = Settings()
