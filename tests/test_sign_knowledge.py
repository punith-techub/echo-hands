"""
Unit tests for CORE.sign_knowledge
"""
import pytest
from CORE.sign_knowledge import (
    ALPHANUMERIC_CLASSES,
    CLASS_TO_INDEX,
    INDEX_TO_CLASS,
    ISL_WORDS_METADATA,
    ALL_SIGNS,
    get_sign_info,
    is_alphanumeric,
    is_word,
    get_all_alphanumeric_classes,
    get_all_words,
    get_class_index,
    get_label_from_index,
    search_signs
)

def test_alphanumeric_classes_count_and_types():
    assert len(ALPHANUMERIC_CLASSES) == 35
    # Digits 1-9
    for d in range(1, 10):
        assert str(d) in ALPHANUMERIC_CLASSES
    # Letters A-Z
    import string
    for letter in string.ascii_uppercase:
        assert letter in ALPHANUMERIC_CLASSES

def test_bijective_indexing():
    assert len(CLASS_TO_INDEX) == 35
    assert len(INDEX_TO_CLASS) == 35
    for idx, cls in enumerate(ALPHANUMERIC_CLASSES):
        assert CLASS_TO_INDEX[cls] == idx
        assert INDEX_TO_CLASS[idx] == cls
        assert get_class_index(cls) == idx
        assert get_label_from_index(idx) == cls

def test_invalid_class_indexing():
    with pytest.raises(ValueError):
        get_class_index("INVALID_CLASS")
    with pytest.raises(ValueError):
        get_label_from_index(999)

def test_isl_words_catalog():
    words = get_all_words()
    assert len(words) >= 50
    # Key vocabulary checks
    assert "NAMASTE" in words
    assert "HELLO" in words
    assert "HELP" in words
    assert "THANK_YOU" in words
    assert "PLEASE" in words
    assert "SORRY" in words
    assert "FOOD" in words
    assert "WATER" in words

def test_sign_info_metadata_integrity():
    for sign_name in ["A", "5", "NAMASTE", "HELP", "FOOD"]:
        info = get_sign_info(sign_name)
        assert info is not None
        assert "label" in info
        assert "hindi" in info
        assert "translit" in info
        assert "phonetic" in info
        assert "handedness" in info
        assert info["handedness"] in ("one-handed", "two-handed")

def test_predicate_functions():
    assert is_alphanumeric("A") is True
    assert is_alphanumeric("7") is True
    assert is_alphanumeric("NAMASTE") is False

    assert is_word("NAMASTE") is True
    assert is_word("HELP") is True
    assert is_word("1") is False

def test_search_signs():
    results = search_signs("namaste")
    assert len(results) >= 1
    assert results[0]["label"] == "NAMASTE"

    hindi_results = search_signs("नमस्ते")
    assert len(hindi_results) >= 1
