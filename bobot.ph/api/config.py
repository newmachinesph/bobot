from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Redis
    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: str

    # R2 Storage
    R2_ENDPOINT_URL: str
    R2_ACCESS_KEY_ID: str
    R2_SECRET_ACCESS_KEY: str

    # Auth
    SECRET_KEY: str = "dev-secret-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days

    # API
    API_BASE_URL: str = "http://localhost:8000"
    ENVIRONMENT: str = "development"

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # Remove params not supported by asyncpg
        for param in ["channel_binding=require", "sslmode=require"]:
            url = url.replace(f"&{param}", "")
            url = url.replace(f"?{param}&", "?")
            url = url.replace(f"?{param}", "")
        # Clean up trailing ? if all params removed
        if url.endswith("?"):
            url = url[:-1]
        return url

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()  # type: ignore[call-arg]
