from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "scheduler"
    host: str = "0.0.0.0"
    port: int = 8003

    model_config = {"env_prefix": "SCHEDULER_"}
