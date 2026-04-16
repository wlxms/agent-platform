from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "billing"
    host: str = "0.0.0.0"
    port: int = 8006

    model_config = {"env_prefix": "BILLING_"}
