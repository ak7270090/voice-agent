"""Speech-to-text and voice plugins for an agent's "provider/model" settings."""

from livekit.agents import NOT_GIVEN, stt, tts
from livekit.plugins import openai

from studio_runtime.config import Settings
from studio_runtime.control_plane import VoiceSettings

OPENAI_PROVIDER = "openai"
SUPPORTED_PROVIDERS = (OPENAI_PROVIDER,)
# Raw PCM starts playing without an MP3 decode step (the plugin's default is MP3).
OPENAI_TTS_FORMAT = "pcm"


class UnsupportedProviderError(ValueError):
    pass


def split_model(spec: str) -> tuple[str, str]:
    provider, separator, model = spec.partition("/")
    if not separator or not model:
        raise UnsupportedProviderError(f"expected 'provider/model', got {spec!r}")
    if provider not in SUPPORTED_PROVIDERS:
        raise UnsupportedProviderError(f"{provider!r} is not one of {SUPPORTED_PROVIDERS}")
    return provider, model


def create_stt(voice: VoiceSettings, language: str, settings: Settings) -> stt.STT:
    _, model = split_model(voice.stt_model)
    return openai.STT(model=model, language=language, use_realtime=settings.stt_streaming)


def create_tts(voice: VoiceSettings) -> tts.TTS:
    _, model = split_model(voice.tts_model)
    return openai.TTS(
        model=model, voice=voice.voice, instructions=NOT_GIVEN, response_format=OPENAI_TTS_FORMAT
    )
