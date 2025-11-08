"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    DATABASE_CLIENT: str = "postgres"
    DATABASE_HOST: str
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str
    DATABASE_USERNAME: str
    DATABASE_PASSWORD: str
    DATABASE_SSL: bool = False

    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from components"""
        return (
            f"postgresql://{self.DATABASE_USERNAME}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Pinpoint API"
    DEBUG: bool = True
    ALLOWED_ORIGINS: str = "*"

    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Parse CORS origins from string"""
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # Redis (optional)
    REDIS_URL: str = "redis://localhost:6379"

    # Firebase Cloud Messaging
    FCM_CREDENTIALS_PATH: str = "firebase-admin-sdk.json"

    # Google Play
    GOOGLE_PLAY_SERVICE_ACCOUNT_PATH: str = "google-play-service-account.json"
    GOOGLE_PLAY_PACKAGE_NAME: str = "com.pinpoint.app"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
