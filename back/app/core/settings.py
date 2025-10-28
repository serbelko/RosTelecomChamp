from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str
    ASYNC_DATABASE_URL: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    SECRET_KEY: str
    PASSWORD_MIN_LENGTH: int
    ALGORITHM: str = "HS256"
    ISSUER: str | None = None 
    AUDIENCE: str | None = None
    REDIS_URL: str | None = None



    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
