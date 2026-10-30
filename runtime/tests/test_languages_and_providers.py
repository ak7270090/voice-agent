import pytest
from livekit.plugins import openai

from studio_runtime.config import Settings
from studio_runtime.control_plane import VoiceSettings
from studio_runtime.languages import UnsupportedLanguageError, build_instructions, load_locale
from studio_runtime.providers import UnsupportedProviderError, create_stt, create_tts, split_model

VOICE = VoiceSettings(
    stt_model="openai/gpt-4o-mini-transcribe", tts_model="openai/tts-1", voice="alloy"
)


def test_english_locale_has_prompt_rules_and_messages():
    locale = load_locale("en")

    assert "Reply in English." in locale.prompt_rules
    assert locale.messages["agent_unavailable"]


def test_instructions_are_the_agents_own_followed_by_the_language_rules():
    instructions = build_instructions("  Be the front desk.\n", load_locale("en"))

    assert instructions.startswith("Be the front desk.\n\nReply in English.")


def test_language_without_a_locale_folder_is_unsupported():
    with pytest.raises(UnsupportedLanguageError):
        load_locale("xx")


@pytest.mark.parametrize("spec", ["tts-1", "openai/", "acme/voice-1"])
def test_bad_or_unknown_provider_specs_are_rejected(spec):
    with pytest.raises(UnsupportedProviderError):
        split_model(spec)


def test_openai_speech_plugins_are_built_from_the_agents_voice(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    speech_to_text = create_stt(VOICE, "en", Settings())
    voice = create_tts(VOICE)

    assert isinstance(speech_to_text, openai.STT)
    assert isinstance(voice, openai.TTS)
    assert voice.model == "tts-1"
