from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "host"
    host: str = "0.0.0.0"
    port: int = 8002

    model_config = {"env_prefix": "HOST_"}
