from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:changeme_secure_password@localhost:5432/habits_db"
    JWT_SECRET: str = "dev-secret-key-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REDIS_URL: str = "redis://localhost:6379/2"
    LOG_LEVEL: str = "info"
    CORS_ORIGINS: list[str] = ["http://localhost:3020"]

    model_config = {"env_file": "../.env.local", "extra": "ignore"}


settings = Settings()
