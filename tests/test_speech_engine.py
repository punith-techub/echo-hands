"""
Unit tests for CORE.speech_engine
"""
import pytest
from CORE.speech_engine import SpeechEngine

@pytest.fixture
def engine():
    return SpeechEngine()

def test_speech_locales(engine):
    assert "en-IN" in engine.supported_locales
    assert "hi-IN" in engine.supported_locales

def test_generate_tts_metadata_english(engine):
    payload = engine.generate_tts_metadata(
        english_sentence="Hello! How are you?",
        hindi_sentence="नमस्ते! आप कैसे हैं?",
        preferred_lang="en-IN"
    )
    assert payload["primary"]["lang"] == "en-IN"
    assert payload["primary"]["text"] == "Hello! How are you?"
    assert payload["primary"]["rate"] > 0
    assert payload["primary"]["pitch"] > 0
    assert len(payload["waveform_pattern"]) == 32
    assert all(0.0 <= v <= 1.0 for v in payload["waveform_pattern"])

def test_generate_tts_metadata_hindi(engine):
    payload = engine.generate_tts_metadata(
        english_sentence="Please help me.",
        hindi_sentence="कृपया मेरी मदद कीजिए।",
        preferred_lang="hi-IN"
    )
    assert payload["primary"]["lang"] == "hi-IN"
    assert payload["primary"]["text"] == "कृपया मेरी मदद कीजिए।"
    assert payload["secondary"]["lang"] == "en-IN"

def test_phonetic_hint_extraction(engine):
    hint = engine.generate_phonetic_hint("Namaste friend", "नमस्ते दोस्त", "en-IN")
    assert isinstance(hint, str)
    assert len(hint) > 0
