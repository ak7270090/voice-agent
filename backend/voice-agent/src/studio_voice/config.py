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
    # Processes kept warm for the next calls (one call per process); LiveKit's default is 8.
    num_idle_processes: int = 2

    api_url: str = "http://localhost:8000"
    runtime_api_token: str = ""
    api_timeout_seconds: float = 5.0

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"

    stt_streaming: bool = True

    # Turn-taking. LiveKit's turn detector listens to the audio to tell a finished sentence from
    # a pause; "" lets LiveKit choose (v1 on LiveKit Cloud, else the local v1-mini).
    turn_detector_version: str = ""
    # "dynamic" adapts the wait to each caller's pauses (LiveKit's turn-tuning guide).
    endpointing_mode: str = "dynamic"
    min_endpointing_delay: float = 0.4
    max_endpointing_delay: float = 2.0
    interruption_mode: str = "adaptive"
    min_interruption_duration: float = 0.5
    # Off: a reply drafted before the turn ends is thrown away if the caller goes on, but its
    # tools may already have moved the flow or booked a slot (clinic-voice-agent found the same).
    preemptive_generation: bool = False
    # A voice caller silent this long (and the agent too) is asked "Are you still there?".
    caller_away_seconds: float = 12.0
    # A tool's "say while it runs" line plays only if the tool is still running after this.
    filler_delay_seconds: float = 0.7
    # Flows read "tomorrow" and "Saturday" in this time zone.
    timezone: str = "Asia/Kolkata"
    # A caller hears silence while a tool runs: give up after this and say so instead.
    tool_timeout_seconds: float = 3.0
    # OpenAI GPT-5 models think before answering by default; "none" answers at once, "" keeps
    # the model's default. Measured with the scenario run (31 October 2026): "none" made the
    # model skip save_fields and the availability check, failing "change a detail" twice, and
    # replies were no faster (median 1.15 s vs 0.88 s), so the default is kept.
    llm_reasoning_effort: str = ""
    llm_max_retries: int = 2
    # Longest wait for the model before a request is cut off and retried (FlowGraph, LangGraph).
    llm_timeout_seconds: float = 10.0
    llm_retry_delay_seconds: float = 0.5

    # Outgoing calls: LiveKit's answering-machine detection classifies the first words with
    # this model through LiveKit Inference (it needs LiveKit's own tool calls, which the
    # LangChain adapter does not pass on). "" skips detection and greets whoever answers.
    amd_llm_model: str = "openai/gpt-4.1-mini"


@lru_cache
def get_settings() -> Settings:
    return Settings()
