from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "auth"
    host: str = "0.0.0.0"
    port: int = 8001

    model_config = {"env_prefix": "AUTH_"}
