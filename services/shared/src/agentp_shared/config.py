"""Service ports, URLs, and configuration classes."""
from pydantic_settings import BaseSettings

# Service ports
GATEWAY_PORT = 8000
AUTH_PORT = 8001
HOST_PORT = 8002
SCHEDULER_PORT = 8003
MEMORY_PORT = 8004
MARKET_PORT = 8005
BILLING_PORT = 8006

# Service URLs
AUTH_URL = f"http://localhost:{AUTH_PORT}"
HOST_URL = f"http://localhost:{HOST_PORT}"
SCHEDULER_URL = f"http://localhost:{SCHEDULER_PORT}"
MEMORY_URL = f"http://localhost:{MEMORY_PORT}"
MARKET_URL = f"http://localhost:{MARKET_PORT}"
BILLING_URL = f"http://localhost:{BILLING_PORT}"


class DatabaseSettings(BaseSettings):
    url: str = "postgresql+asyncpg://agentp:agentp_dev@localhost:5432/agent_platform"
    echo: bool = False
    pool_size: int = 10
    model_config = {"env_prefix": "AGENTP_DB_"}


class RedisSettings(BaseSettings):
    url: str = "redis://localhost:6379/0"
    model_config = {"env_prefix": "AGENTP_REDIS_"}


class JWTSettings(BaseSettings):
    secret_key: str = "agentp-dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 24 * 60
    refresh_token_expire_days: int = 7
    model_config = {"env_prefix": "AGENTP_JWT_"}


class Settings(BaseSettings):
    debug: bool = False
    model_config = {"env_prefix": "AGENTP_"}


db_settings = DatabaseSettings()
redis_settings = RedisSettings()
jwt_settings = JWTSettings()
settings = Settings()
