"""Speech-to-text and voice plugins for an agent's "provider/model" settings."""

from livekit.agents import (
    NOT_GIVEN,
    EndpointingOptions,
    InterruptionOptions,
    TurnHandlingOptions,
    inference,
    stt,
    tts,
)
from livekit.plugins import cartesia, deepgram, openai

from studio_voice.core.backend_client import VoiceSettings
from studio_voice.core.config import Settings

OPENAI_PROVIDER = "openai"
DEEPGRAM_PROVIDER = "deepgram"
CARTESIA_PROVIDER = "cartesia"
STT_PROVIDERS = (OPENAI_PROVIDER, DEEPGRAM_PROVIDER)
TTS_PROVIDERS = (OPENAI_PROVIDER, CARTESIA_PROVIDER, DEEPGRAM_PROVIDER)
# Raw PCM starts playing without an MP3 decode step (the plugin's default is MP3).
OPENAI_TTS_FORMAT = "pcm"
# Deepgram wants a region code; agents store plain language codes.
DEEPGRAM_LANGUAGES = {"en": "en-US", "hi": "hi"}


class UnsupportedProviderError(ValueError):
    pass


def split_model(spec: str, supported: tuple[str, ...]) -> tuple[str, str]:
    provider, separator, model = spec.partition("/")
    if not separator or not model:
        raise UnsupportedProviderError(f"expected 'provider/model', got {spec!r}")
    if provider not in supported:
        raise UnsupportedProviderError(f"{provider!r} is not one of {supported}")
    return provider, model


def create_stt(voice: VoiceSettings, language: str, settings: Settings) -> stt.STT:
    provider, model = split_model(voice.stt_model, STT_PROVIDERS)
    if provider == DEEPGRAM_PROVIDER:
        return deepgram.STT(model=model, language=DEEPGRAM_LANGUAGES.get(language, language))
    return openai.STT(model=model, language=language, use_realtime=settings.stt_streaming)


def create_tts(voice: VoiceSettings, language: str) -> tts.TTS:
    provider, model = split_model(voice.tts_model, TTS_PROVIDERS)
    if provider == DEEPGRAM_PROVIDER:
        # Deepgram's voice is part of the model name, e.g. aura-2-thalia-en.
        return deepgram.TTS(model=model)
    if provider == CARTESIA_PROVIDER:
        # Cartesia voices are ids; an empty voice keeps the plugin's default voice.
        options = {"voice": voice.voice} if voice.voice else {}
        return cartesia.TTS(model=model, language=language, **options)
    return openai.TTS(
        model=model, voice=voice.voice, instructions=NOT_GIVEN, response_format=OPENAI_TTS_FORMAT
    )


def build_turn_handling(settings: Settings) -> TurnHandlingOptions:
    version = settings.turn_detector_version or NOT_GIVEN
    return TurnHandlingOptions(
        turn_detection=inference.TurnDetector(version=version),
        endpointing=EndpointingOptions(
            mode=settings.endpointing_mode,
            min_delay=settings.min_endpointing_delay,
            max_delay=settings.max_endpointing_delay,
        ),
        interruption=InterruptionOptions(
            mode=settings.interruption_mode,
            min_duration=settings.min_interruption_duration,
        ),
        preemptive_generation={"enabled": settings.preemptive_generation},
    )
