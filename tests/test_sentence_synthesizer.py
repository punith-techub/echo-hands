"""
Unit tests for CORE.sentence_synthesizer
"""
import pytest
from CORE.sentence_synthesizer import SentenceSynthesizer

@pytest.fixture
def synthesizer():
    return SentenceSynthesizer()

def test_fingerspelling_aggregation_letters(synthesizer):
    raw = ["H", "E", "L", "L", "O"]
    agg = synthesizer.aggregate_fingerspelling(raw)
    assert agg == ["HELLO"]

def test_fingerspelling_aggregation_cat(synthesizer):
    raw = ["C", "A", "T"]
    agg = synthesizer.aggregate_fingerspelling(raw)
    assert agg == ["CAT"]

def test_fingerspelling_mixed_with_words(synthesizer):
    raw = ["I", "W", "A", "N", "T", "FOOD"]
    agg = synthesizer.aggregate_fingerspelling(raw)
    assert "FOOD" in agg

def test_greeting_patterns(synthesizer):
    res_namaste = synthesizer.synthesize(["NAMASTE"])
    assert "Namaste" in res_namaste["english_sentence"]
    assert "नमस्ते" in res_namaste["hindi_sentence"]

    res_morning = synthesizer.synthesize(["GOOD_MORNING"])
    assert "Good morning" in res_morning["english_sentence"]
    assert "सुप्रभात" in res_morning["hindi_sentence"]

def test_emergency_help_patterns(synthesizer):
    res = synthesizer.synthesize(["PLEASE", "HELP", "ME"])
    assert "Please help me" in res["english_sentence"]
    assert "मदद" in res["hindi_sentence"]

def test_isl_sov_to_svo_restructuring(synthesizer):
    # ISL SOV: I FOOD EAT -> English SVO: I want to eat food.
    res = synthesizer.synthesize(["I", "FOOD", "EAT"])
    assert "I" in res["english_sentence"]
    assert "food" in res["english_sentence"].lower()
    assert "खाना" in res["hindi_sentence"]

def test_question_restructuring(synthesizer):
    res = synthesizer.synthesize(["YOU", "NAME", "WHAT"])
    assert res["has_question"] is True
    assert "What is your name?" == res["english_sentence"]
    assert "नाम" in res["hindi_sentence"]

def test_empty_tokens(synthesizer):
    res = synthesizer.synthesize([])
    assert res["english_sentence"] == ""
    assert res["hindi_sentence"] == ""
    assert res["aggregated_tokens"] == []
