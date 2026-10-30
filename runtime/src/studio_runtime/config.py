"""Runtime settings, read from the environment and `.env.local` (repository root or `runtime/`)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env.local", ".env.local"), extra="ignore")

    agent_name: str = "studio-agent"
    health_port: int = 8081
    worker_load_threshold: float = 0.7


@lru_cache
def get_settings() -> Settings:
    return Settings()
