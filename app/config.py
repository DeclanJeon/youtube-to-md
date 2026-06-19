from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cache_max_size: int = 1000
    cache_ttl_seconds: int = 3600
    request_timeout: int = 30
    rate_limit_per_minute: int = 10
    log_level: str = "INFO"
    cors_origins: str = "*"
    youtube_api_key: str | None = None

    model_config = {"env_prefix": "", "case_sensitive": False, "env_file": ".env"}


settings = Settings()
