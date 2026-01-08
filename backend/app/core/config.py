from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/bump_aware"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Bump Aware API"
    DEBUG: bool = True
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8081"

    # Validation
    MIN_DETECTIONS_FOR_HAZARD: int = 3
    SPATIAL_CLUSTER_RADIUS_METERS: float = 15.0
    TEMPORAL_WEIGHT_DAYS: int = 30
    CONFIDENCE_DECAY_DAYS: int = 90
    MAX_GPS_ACCURACY_METERS: float = 10.0

    # Alert Settings
    MIN_ALERT_DISTANCE_METERS: float = 50.0
    MAX_ALERT_DISTANCE_METERS: float = 1000.0
    ALERT_SUPPRESSION_RADIUS_METERS: float = 500.0

    # Data Retention
    OLD_DETECTION_RETENTION_DAYS: int = 90

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
