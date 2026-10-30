"""API settings, read from the environment and `.env.local` (repository root or `api/`)."""

from functools import lru_cache
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILES = ("../.env.local", ".env.local")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILES, extra="ignore")

    database_url: str = "postgresql+asyncpg://studio:studio@localhost:5432/studio"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "studio"
    s3_secret_key: str = "studio-secret"
    s3_bucket: str = "studio"
    s3_region: str = "us-east-1"
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

    # Knowledge bases. Changing the embedding model's size needs a migration (chunks.embedding).
    embedding_model: str = "openai:text-embedding-3-small"
    max_upload_bytes: int = 20 * 1024 * 1024
    chunk_size_chars: int = 800
    chunk_overlap_chars: int = 120
    knowledge_top_k: int = 3
    # Chunks taken from the vector index before the keyword boost re-ranks them.
    knowledge_candidate_count: int = 20
    # Weight of question-word overlap added to cosine similarity (0.1 fixed a miss in the clinic).
    knowledge_keyword_weight: float = 0.1


@lru_cache
def get_settings() -> Settings:
    return Settings()


def export_provider_keys() -> None:
    """LangChain reads provider keys (OPENAI_API_KEY, ...) from the process environment, which
    Docker fills from .env.local; this does the same for a locally started API or worker."""
    for env_file in ENV_FILES:
        load_dotenv(env_file, override=False)


SettingsDep = Annotated[Settings, Depends(get_settings)]
