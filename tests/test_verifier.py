"""
Unit tests for ECHOHANDS 5.0 AIVerifier and Multi-Key Fallback Engine
Verifies:
1. Internet connectivity check.
2. Key slot discovery and initialization.
3. Zero Context Loss across fallback transitions and multi-turn conversations.
4. Fallback execution when primary slot hits rate limit / error.
5. Offline fallback behavior when all slots are exhausted.
6. Verification schema compliance (is_correct, wrong_sign, correct_sign, etc.).
"""

import os
import pytest
from unittest.mock import MagicMock, patch

from CORE.verifier import AIVerifier, APIKeySlot, VerificationContext


def test_verification_context_zero_loss():
    ctx = VerificationContext(session_id="test_session_1")
    assert ctx.get_context_summary() == "No previous sentences in this session."

    # Turn 1
    ctx.add_turn(["HELLO"], "Hello.", "Hello! Greetings.")
    assert len(ctx.history) == 1
    assert "HELLO" in ctx.recent_signs
    assert "Hello! Greetings." in ctx.recent_sentences

    # Turn 2
    ctx.add_turn(["I", "WATER", "WANT"], "I want water.", "I would like to drink water.")
    assert len(ctx.history) == 2
    assert "WATER" in ctx.recent_signs
    summary = ctx.get_context_summary()
    assert "Hello! Greetings." in summary
    assert "I would like to drink water." in summary


def test_internet_connectivity_check():
    verifier = AIVerifier(key_slots=[])
    # Fast check should return a boolean without throwing exceptions
    connected = verifier.check_internet(force=True)
    assert isinstance(connected, bool)


def test_offline_fallback_when_no_keys():
    verifier = AIVerifier(key_slots=[])
    res = verifier.verify_sentence(
        raw_tokens=["NAMASTE"],
        candidate_en="Namaste.",
        candidate_hi="नमस्ते।",
        actual_confidence=0.915,
        session_id="offline_sess"
    )
    assert res["is_verified"] is False
    assert res["fallback_to_local"] is True
    assert res["verified_sentence_en"] == "Namaste."
    assert res["verified_sentence_hi"] == "नमस्ते।"


def test_key_slot_fallback_on_rate_limit_with_zero_context_loss():
    """
    Test that when Slot 1 fails with 429 RateLimit, Slot 2 is called
    immediately with the exact same context (zero context loss).
    """
    slot1 = APIKeySlot(
        provider="groq",
        key="key_1",
        model="qwen/qwen3.8-27b",
        name="Slot-1-RateLimited"
    )
    slot2 = APIKeySlot(
        provider="gemini",
        key="key_2",
        model="gemini-2.5-flash",
        name="Slot-2-Backup"
    )

    verifier = AIVerifier(key_slots=[slot1, slot2])

    # Mock dispatch call: slot1 throws 429, slot2 succeeds
    def mock_dispatch(slot, prompt):
        if slot.name == "Slot-1-RateLimited":
            raise Exception("Error code: 429 - {'error': {'message': 'Rate limit exceeded'}}")
        elif slot.name == "Slot-2-Backup":
            return {
                "is_correct": True,
                "wrong_sign": "",
                "correct_sign": "",
                "verified_sentence_en": "Please help me!",
                "verified_sentence_hi": "कृपया मेरी मदद करें!",
                "explanation": "Gesture sequence correctly indicates emergency request."
            }
        raise ValueError("Unknown slot")

    with patch.object(verifier, "_dispatch_call", side_effect=mock_dispatch), \
         patch.object(verifier, "check_internet", return_value=True):

        res = verifier.verify_sentence(
            raw_tokens=["HELP", "ME"],
            candidate_en="Help me.",
            candidate_hi="मेरी मदद करो।",
            actual_confidence=0.892,
            session_id="fallback_session"
        )

        assert res["is_verified"] is True
        assert res["fallback_to_local"] is False
        assert res["key_name"] == "Slot-2-Backup"
        assert res["provider_used"] == "gemini (gemini-2.5-flash)"
        assert res["is_correct"] is True
        assert res["verified_sentence_en"] == "Please help me!"
        assert any("Slot-1-RateLimited" in shift for shift in res["shifted_keys"])
        assert slot1.is_exhausted is True


def test_verifier_detects_wrong_prediction_and_provides_correction():
    slot = APIKeySlot(
        provider="groq",
        key="mock_key",
        model="qwen/qwen3.8-27b",
        name="Slot-Active"
    )
    verifier = AIVerifier(key_slots=[slot])

    mock_json = {
        "is_correct": False,
        "wrong_sign": "1",
        "correct_sign": "I",
        "verified_sentence_en": "I need food.",
        "verified_sentence_hi": "मुझे खाना चाहिए।",
        "explanation": "Digit '1' was misclassified for pronoun 'I' in sentence context."
    }

    with patch.object(verifier, "_dispatch_call", return_value=mock_json), \
         patch.object(verifier, "check_internet", return_value=True):

        res = verifier.verify_sentence(
            raw_tokens=["1", "FOOD", "NEED"],
            candidate_en="1 food need.",
            candidate_hi="1 खाना चाहिए।",
            actual_confidence=0.74,
            session_id="correction_sess"
        )

        assert res["is_verified"] is True
        assert res["is_correct"] is False
        assert res["wrong_sign"] == "1"
        assert res["correct_sign"] == "I"
        assert res["verified_sentence_en"] == "I need food."
        assert res["verified_sentence_hi"] == "मुझे खाना चाहिए।"


def test_all_keys_exhausted_smooth_fallback_to_local():
    slot1 = APIKeySlot("groq", "k1", "m1", "Slot-1", is_exhausted=True, exhausted_until=9999999999.0)
    slot2 = APIKeySlot("gemini", "k2", "m2", "Slot-2", is_exhausted=True, exhausted_until=9999999999.0)

    verifier = AIVerifier(key_slots=[slot1, slot2])

    with patch.object(verifier, "check_internet", return_value=True):
        res = verifier.verify_sentence(
            raw_tokens=["WATER"],
            candidate_en="Water.",
            candidate_hi="पानी।",
            actual_confidence=0.912,
            session_id="all_exhausted"
        )

        assert res["is_verified"] is False
        assert res["fallback_to_local"] is True
        assert res["verified_sentence_en"] == "Water."
        assert "exhausted" in res["explanation"].lower()


def test_verifier_multi_key_numbered_discovery():
    test_env = {
        "GROQ_API_KEY_1": "gsk_test_key_alpha",
        "GROQ_API_KEY_2": "gsk_test_key_beta",
        "GEMINI_API_KEY_PRIMARY": "gemini_test_key_gamma",
        "OPENAI_API_KEY": "sk_test_key_delta"
    }
    with patch.dict(os.environ, test_env, clear=False):
        verifier = AIVerifier()
        slot_names = [s.name for s in verifier.key_slots]
        providers = [s.provider for s in verifier.key_slots]
        keys = [s.key for s in verifier.key_slots]

        assert "gsk_test_key_alpha" in keys
        assert "gsk_test_key_beta" in keys
        assert "gemini_test_key_gamma" in keys
        assert "sk_test_key_delta" in keys
        assert "groq" in providers
        assert "gemini" in providers
        assert "openai" in providers


def test_verifier_preserves_context_across_offline_and_online_shift():
    """
    Verify zero context loss:
    1. Turn 1 happens while offline -> added to session context.
    2. Turn 2 comes online -> verifier includes Turn 1 in context summary!
    """
    slot = APIKeySlot("groq", "key_active", "qwen/qwen3.8-27b", "Groq-Active")
    verifier = AIVerifier(key_slots=[slot])
    sess = "cross_shift_session"

    # Turn 1: Offline
    with patch.object(verifier, "check_internet", return_value=False):
        res1 = verifier.verify_sentence(
            raw_tokens=["HELLO"],
            candidate_en="Hello.",
            candidate_hi="नमस्ते।",
            actual_confidence=0.91,
            session_id=sess
        )
        assert res1["fallback_to_local"] is True

    # Turn 2: Online with captured prompt inspection
    captured_prompt = []
    def mock_dispatch(s, prompt):
        captured_prompt.append(prompt)
        return {
            "is_correct": True,
            "wrong_sign": "",
            "correct_sign": "",
            "verified_sentence_en": "I need help.",
            "verified_sentence_hi": "मुझे मदद चाहिए।",
            "explanation": "Correct."
        }

    with patch.object(verifier, "_dispatch_call", side_effect=mock_dispatch), \
         patch.object(verifier, "check_internet", return_value=True):
        res2 = verifier.verify_sentence(
            raw_tokens=["HELP"],
            candidate_en="Help.",
            candidate_hi="मदद।",
            actual_confidence=0.88,
            session_id=sess
        )
        assert res2["is_verified"] is True
        assert len(captured_prompt) == 1
        # ZERO context loss: The previous offline sentence must appear in the prompt summary!
        assert "Hello." in captured_prompt[0]


def test_verifier_in_flight_token_cache():
    slot = APIKeySlot("groq", "k1", "m1", "Slot-1")
    verifier = AIVerifier(key_slots=[slot])
    sess = "cache_sess"

    dispatch_counter = [0]
    def mock_dispatch(s, prompt):
        dispatch_counter[0] += 1
        return {
            "is_correct": True,
            "wrong_sign": "",
            "correct_sign": "",
            "verified_sentence_en": "Namaste.",
            "verified_sentence_hi": "नमस्ते।",
            "explanation": "Verified."
        }

    with patch.object(verifier, "_dispatch_call", side_effect=mock_dispatch), \
         patch.object(verifier, "check_internet", return_value=True):

        # Call 1: fresh
        res1 = verifier.verify_sentence(["NAMASTE"], "Namaste.", "नमस्ते।", 0.90, session_id=sess)
        assert dispatch_counter[0] == 1
        assert res1["is_verified"] is True

        # Call 2: identical tokens immediately after -> hits cache without dispatching network call
        res2 = verifier.verify_sentence(["NAMASTE"], "Namaste.", "नमस्ते।", 0.90, session_id=sess)
        assert dispatch_counter[0] == 1
        assert res2.get("is_cached") is True

        # Call 3: new token -> immediately bypasses cache and dispatches!
        res3 = verifier.verify_sentence(["HELP"], "Help.", "मदद।", 0.90, session_id=sess)
        assert dispatch_counter[0] == 2
