from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "gateway"
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_prefix": "GATEWAY_"}
