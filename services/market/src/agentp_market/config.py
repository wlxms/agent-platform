from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "market"
    host: str = "0.0.0.0"
    port: int = 8005

    model_config = {"env_prefix": "MARKET_"}
