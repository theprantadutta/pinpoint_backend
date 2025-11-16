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


    # Firebase Cloud Messaging
    FCM_CREDENTIALS_PATH: str = "firebase-admin-sdk.json"

    # Firebase Authentication
    FIREBASE_PROJECT_ID: str
    FIREBASE_AUTH_ENABLED: bool = False
    GOOGLE_WEB_CLIENT_ID: str

    # Google Play
    GOOGLE_PLAY_SERVICE_ACCOUNT_PATH: str = "google-play-service-account.json"
    GOOGLE_PLAY_PACKAGE_NAME: str = "com.pinpoint.app"

    # Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_FROM_NAME: str = "Pinpoint"

    # Subscription Settings
    GRACE_PERIOD_DAYS: int = 3  # Grace period after payment failure
    TRIAL_PERIOD_DAYS: int = 7  # Free trial period

    # Admin Panel Configuration
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str
    ADMIN_JWT_EXPIRE_MINUTES: int = 60  # 1 hour for admin sessions

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
