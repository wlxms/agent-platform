from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "memory"
    host: str = "0.0.0.0"
    port: int = 8004

    model_config = {"env_prefix": "MEMORY_"}
