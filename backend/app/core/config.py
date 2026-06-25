from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Required secrets — intentionally have NO defaults so a missing or empty value
    # fails fast at startup instead of silently falling back to an insecure credential.
    DATABASE_URL: str = Field(min_length=1)
    JWT_SECRET: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REDIS_URL: str = "redis://localhost:6379/2"
    LOG_LEVEL: str = "info"
    CORS_ORIGINS: list[str] = ["http://localhost:3020"]

    model_config = {"env_file": "../.env.local", "extra": "ignore"}


settings = Settings()
