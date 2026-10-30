"""Runtime settings, read from the environment and `.env.local` (repository root or `runtime/`).

LiveKit and model-provider keys (LIVEKIT_*, OPENAI_API_KEY) are read by their SDKs directly.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env.local", ".env.local"), extra="ignore")

    agent_name: str = "studio-agent"
    health_port: int = 8081
    worker_load_threshold: float = 0.7

    api_url: str = "http://localhost:8000"
    runtime_api_token: str = ""
    api_timeout_seconds: float = 5.0

    stt_streaming: bool = True
    # Flows read "tomorrow" and "Saturday" in this time zone.
    timezone: str = "Asia/Kolkata"
    tool_timeout_seconds: float = 10.0
    llm_max_retries: int = 2
    llm_retry_delay_seconds: float = 0.5


@lru_cache
def get_settings() -> Settings:
    return Settings()
