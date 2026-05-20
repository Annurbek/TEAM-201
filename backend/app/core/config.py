from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    PROJECT_NAME: str = "Student Ranking System"

    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    SQL_ECHO: bool = False

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:"
            f"{self.DB_PASSWORD}@{self.DB_HOST}:"
            f"{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
