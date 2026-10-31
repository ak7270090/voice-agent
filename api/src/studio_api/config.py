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

    # Requests the runtime makes during a call join that call's trace in Langfuse.
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"
    runtime_api_token: str = ""
    browser_call_token_ttl_minutes: int = 30

    # Starting values for new agents; each agent keeps its own copy.
    # Deepgram for both: in the voice demo it cut transcription from ~960 to ~450 ms and the
    # voice's first audio from 1-2 s to 0.3-1 s against OpenAI's (31 October 2026).
    default_llm_model: str = "openai:gpt-5.4-mini"
    default_stt_model: str = "deepgram/nova-3"
    default_tts_model: str = "deepgram/aura-2-thalia-en"
    default_voice: str = ""
    # Where the runtime reaches the demo clinic API used by the clinic template's tools.
    demo_clinic_api_url: str = "http://api:8000"

    # Campaigns: how often the dialler looks for contacts to call, and how long a call may stay
    # "calling" before it counts as not answered (a runtime that never reported back).
    dialler_interval_seconds: int = 10
    campaign_call_timeout_minutes: int = 15

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
