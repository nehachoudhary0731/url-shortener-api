from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    BASE_URL: str = "http://localhost:8000"
    SHORT_CODE_LENGTH: int = 7
    RATE_LIMIT_PER_MINUTE: int = 10

    class Config:
        env_file = ".env"


settings = Settings()
