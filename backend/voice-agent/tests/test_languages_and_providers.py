import pytest
from livekit.plugins import cartesia, deepgram, openai

from studio_voice.call.speech_providers import (
    UnsupportedProviderError,
    create_stt,
    create_tts,
    split_model,
)
from studio_voice.core.backend_client import VoiceSettings
from studio_voice.core.config import Settings
from studio_voice.languages import UnsupportedLanguageError, build_instructions, load_locale

VOICE = VoiceSettings(
    stt_model="openai/gpt-4o-mini-transcribe", tts_model="openai/tts-1", voice="alloy"
)


def test_english_locale_has_prompt_rules_and_messages():
    locale = load_locale("en")

    assert "Reply in English." in locale.prompt_rules
    assert locale.messages["agent_unavailable"]


def test_instructions_are_the_agents_own_followed_by_the_language_rules():
    instructions = build_instructions("  Be the front desk.\n", load_locale("en"), False)

    assert instructions.startswith("Be the front desk.\n\nReply in English.")
    assert "search_knowledge" not in instructions


def test_agents_with_documents_are_told_to_search_them_first():
    instructions = build_instructions("Be the front desk.", load_locale("en"), True)

    assert instructions.endswith(load_locale("en").messages["knowledge_rule"])


def test_language_without_a_locale_folder_is_unsupported():
    with pytest.raises(UnsupportedLanguageError):
        load_locale("xx")


@pytest.mark.parametrize("spec", ["tts-1", "openai/", "acme/voice-1"])
def test_bad_or_unknown_provider_specs_are_rejected(spec):
    with pytest.raises(UnsupportedProviderError):
        split_model(spec, ("openai",))


def test_openai_speech_plugins_are_built_from_the_agents_voice(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    speech_to_text = create_stt(VOICE, "en", Settings())
    voice = create_tts(VOICE, "en")

    assert isinstance(speech_to_text, openai.STT)
    assert isinstance(voice, openai.TTS)
    assert voice.model == "tts-1"


def test_deepgram_and_cartesia_are_built_when_an_agent_names_them(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test")
    monkeypatch.setenv("CARTESIA_API_KEY", "test")
    fast = VoiceSettings(stt_model="deepgram/nova-3", tts_model="cartesia/sonic-3", voice="")

    speech_to_text = create_stt(fast, "en", Settings())
    voice = create_tts(fast, "en")

    assert isinstance(speech_to_text, deepgram.STT)
    assert isinstance(voice, cartesia.TTS)


def test_deepgram_voice_is_named_by_its_model(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test")
    aura = VoiceSettings(
        stt_model="deepgram/nova-3", tts_model="deepgram/aura-2-thalia-en", voice=""
    )

    assert isinstance(create_tts(aura, "en"), deepgram.TTS)
