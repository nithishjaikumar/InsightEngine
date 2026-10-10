from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "InsightEngine"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # MySQL Database Connection URL
    # Primary driver: PyMySQL. Example: mysql+pymysql://username:password@localhost:3306/insightengine
    DATABASE_URL: str = Field(
        default="mysql+pymysql://root:password@localhost:3306/insightengine",
        description="Database connection URL",
    )

    # Ingestion & Upload limits
    MAX_UPLOAD_SIZE_MB: int = 5
    MAX_CSV_ROWS: int = 5000

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
