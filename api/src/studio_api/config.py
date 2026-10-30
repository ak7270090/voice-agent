"""API settings, read from the environment and `.env.local` (repository root or `api/`)."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env.local", ".env.local"), extra="ignore")

    database_url: str = "postgresql+asyncpg://studio:studio@localhost:5432/studio"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint: str = "http://localhost:9000"
    runtime_health_url: str = "http://localhost:8081/"
    cors_origins: list[str] = ["http://localhost:3000"]
    health_check_timeout_seconds: float = 2.0

    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    runtime_agent_name: str = "studio-agent"
    runtime_api_token: str = ""
    browser_call_token_ttl_minutes: int = 30

    # Starting values for new agents; each agent keeps its own copy.
    default_llm_model: str = "openai:gpt-4.1-mini"
    default_stt_model: str = "openai/gpt-4o-mini-transcribe"
    default_tts_model: str = "openai/tts-1"
    default_voice: str = "alloy"


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
