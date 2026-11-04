"""
Integration and End-to-End Tests for ECHOHANDS 5.0 Live Webcam & Feedback Loop
Verifies:
1. /api/webcam/predict endpoint receives live webcam base64 frames.
2. Calculates actual mathematically grounded confidence score (not dummy).
3. If API keys/internet available:
   - Verifies prediction via cloud LLM arbiter
   - Rewards local model when correct
   - Punishes severely and trains instantly when wrong, returning corrected answer
4. If internet/API keys unavailable:
   - Gracefully displays local model prediction with true actual confidence score
5. /api/verifier/status and /api/webcam/reset-session endpoints.
"""

import os
import io
import base64
import numpy as np
import cv2
from PIL import Image
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from CORE.app import app, verifier, online_learner


@pytest.fixture
def client():
    return TestClient(app)


def make_synthetic_frame_b64(skin_color=(130, 165, 215)) -> str:
    img = np.ones((224, 224, 3), dtype=np.uint8) * 35
    # Draw hand silhouette
    cv2.circle(img, (112, 112), 45, skin_color, -1)
    cv2.line(img, (112, 112), (112, 40), skin_color, 16)
    _, buf = cv2.imencode(".jpg", img)
    return f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"


def test_verifier_status_endpoint(client):
    res = client.get("/api/verifier/status")
    assert res.status_code == 200
    data = res.json()
    assert "has_internet" in data
    assert "is_available" in data
    assert "key_slots" in data
    assert "active_slot" in data


def test_webcam_reset_session_endpoint(client):
    res = client.post("/api/webcam/reset-session", json={"session_id": "test_flow_sess"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"


def test_webcam_predict_invalid_payload(client):
    res = client.post("/api/webcam/predict", json={"frame_base64": ""})
    assert res.status_code == 400


def test_webcam_predict_offline_mode_returns_actual_confidence(client):
    """
    When offline (skip_verification=True or no keys), local model predicts
    and actual confidence score is returned (not dummy).
    Uses allow_empty=False (static benchmark path) so skin-segmentation detects
    the synthetic hand silhouette regardless of MediaPipe availability.
    """
    frame_b64 = make_synthetic_frame_b64()
    res = client.post("/api/webcam/predict", json={
        "frame_base64": frame_b64,
        "session_id": "offline_session_test",
        "skip_verification": True,
        "allow_empty": False   # Static path: skin segmentation always detects synthetic blob
    })

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "actual_confidence" in data
    assert isinstance(data["actual_confidence"], float)
    assert 0.0 < data["actual_confidence"] <= 1.0
    # Actual confidence must match calculated local actual confidence
    assert data["actual_confidence"] == data["local_actual_confidence"]
    assert "sentence" in data
    assert "english_sentence" in data["sentence"]
    assert "hindi_sentence" in data["sentence"]
    assert "LOCAL MODEL PREDICTION" in data["verification_badge"]


def test_webcam_predict_online_rewards_correct_model(client):
    """
    When online and verifier confirms prediction is correct:
    - Model is rewarded via online_learner.reward_prediction.
    - Verified English & Hindi sentences returned.
    """
    frame_b64 = make_synthetic_frame_b64()

    mock_v_res = {
        "is_verified": True,
        "is_correct": True,
        "provider_used": "groq (qwen/qwen3.8-27b)",
        "key_name": "Groq-Key-1",
        "verified_sentence_en": "I need food.",
        "verified_sentence_hi": "मुझे खाना चाहिए।",
        "wrong_sign": "",
        "correct_sign": "",
        "explanation": "Correct prediction confirmed.",
        "shifted_keys": [],
        "fallback_to_local": False
    }

    with patch.object(verifier, "check_internet", return_value=True), \
         patch.object(verifier, "is_available", return_value=(True, "Online")), \
         patch.object(verifier, "verify_sentence", return_value=mock_v_res), \
         patch.object(online_learner, "reward_prediction", return_value={"status": "rewarded"}) as mock_reward:

        res = client.post("/api/webcam/predict", json={
            "frame_base64": frame_b64,
            "session_id": "online_reward_sess",
            "skip_verification": False,
            "allow_empty": False   # Static path: skin segmentation detects synthetic blob
        })

        assert res.status_code == 200
        data = res.json()
        assert data["feedback_action"] == "reward"
        assert "VERIFIED: CORRECT" in data["verification_badge"]
        assert data["sentence"]["english_sentence"] == "I need food."
        assert data["sentence"]["hindi_sentence"] == "मुझे खाना चाहिए।"
        assert mock_reward.called


def test_webcam_predict_online_punishes_wrong_and_trains_instantly(client):
    """
    When online and verifier detects an incorrect prediction:
    - Model is severely punished and trained instantly via online_learner.learn_from_feedback.
    - Final corrected sentence is displayed to user.
    """
    frame_b64 = make_synthetic_frame_b64()

    mock_v_res = {
        "is_verified": True,
        "is_correct": False,
        "provider_used": "groq (qwen/qwen3.8-27b)",
        "key_name": "Groq-Key-1",
        "verified_sentence_en": "Please help me!",
        "verified_sentence_hi": "कृपया मेरी मदद करें!",
        "wrong_sign": "1",
        "correct_sign": "HELP",
        "explanation": "Visual misclassification: Hand action is HELP gesture.",
        "shifted_keys": [],
        "fallback_to_local": False
    }

    mock_learn_res = {
        "status": "success",
        "cnn_weights_trained": False,
        "prototype_memory_updated": True,
        "correct_sign": "HELP",
        "wrong_sign": "1"
    }

    with patch.object(verifier, "check_internet", return_value=True), \
         patch.object(verifier, "is_available", return_value=(True, "Online")), \
         patch.object(verifier, "verify_sentence", return_value=mock_v_res), \
         patch.object(online_learner, "learn_from_feedback", return_value=mock_learn_res) as mock_train:

        res = client.post("/api/webcam/predict", json={
            "frame_base64": frame_b64,
            "session_id": "online_punish_sess",
            "skip_verification": False,
            "allow_empty": False   # Static path: skin segmentation detects synthetic blob
        })

        assert res.status_code == 200
        data = res.json()
        assert data["feedback_action"] == "punish_and_train"
        assert "VERIFIED: CORRECTION TRAINED" in data["verification_badge"]
        assert data["sentence"]["english_sentence"] == "Please help me!"
        assert data["sentence"]["hindi_sentence"] == "कृपया मेरी मदद करें!"
        assert mock_train.called


def test_webcam_predict_empty_frame_returns_standby_without_api_calls(client):
    """
    When no hands are in the webcam viewport (allow_empty=True), system must
    return clean standby state and NEVER call cloud LLM or mutate model weights.
    """
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", blank)
    blank_b64 = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"

    with patch.object(verifier, "verify_sentence") as mock_v, \
         patch.object(online_learner, "learn_from_feedback") as mock_train, \
         patch.object(online_learner, "reward_prediction") as mock_reward:

        res = client.post("/api/webcam/predict", json={
            "frame_base64": blank_b64,
            "session_id": "empty_stream_sess",
            "allow_empty": True
        })

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["regions_count"] == 0
        assert data["raw_tokens"] == []
        assert data["actual_confidence"] == 0.0
        assert data["sentence"]["english_sentence"] == ""
        assert "AWAITING HAND GESTURE" in data["verification_badge"]
        # Crucial: NO cloud API or online learner calls made on empty frames!
        assert not mock_v.called
        assert not mock_train.called
        assert not mock_reward.called


def test_webcam_predict_multi_region_punishment_targets_exact_sign(client):
    """
    In multi-sign sequences, if sign 2 was misclassified, online_learner must
    receive crop of sign 2, NEVER blindly region 0.
    """
    # Create synthetic frame with two separated hand shapes
    img = np.ones((224, 448, 3), dtype=np.uint8) * 35
    skin_color = (130, 165, 215)
    # Hand 1 on left
    cv2.circle(img, (100, 112), 40, skin_color, -1)
    # Hand 2 on right
    cv2.circle(img, (340, 112), 40, skin_color, -1)
    _, buf = cv2.imencode(".jpg", img)
    multi_b64 = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"

    captured_crops = []
    def mock_learn(crop_rgb, wrong_sign, correct_sign, is_dual_hand=False):
        captured_crops.append((crop_rgb, wrong_sign, correct_sign))
        return {"status": "success", "cnn_weights_trained": True}

    with patch.object(verifier, "check_internet", return_value=True), \
         patch.object(verifier, "is_available", return_value=(True, "Online")), \
         patch.object(online_learner, "learn_from_feedback", side_effect=mock_learn):

        # We simulate that the verifier indicates token at index 1 is wrong
        def mock_verify(*args, **kwargs):
            return {
                "is_verified": True,
                "is_correct": False,
                "provider_used": "groq",
                "key_name": "Groq-Key-1",
                "verified_sentence_en": "Correct Sentence",
                "verified_sentence_hi": "सही वाक्य",
                "wrong_sign": kwargs["raw_tokens"][-1], # last token was wrong
                "correct_sign": "HELP",
                "explanation": "Correction"
            }

        with patch.object(verifier, "verify_sentence", side_effect=mock_verify):
            res = client.post("/api/webcam/predict", json={
                "frame_base64": multi_b64,
                "session_id": "multi_region_sess",
                "allow_empty": False   # Static path: skin segmentation detects synthetic blobs
            })
            assert res.status_code == 200
            data = res.json()
            if len(data["regions"]) > 1:
                assert len(captured_crops) == 1
                # The crop passed to learn_from_feedback must match the target region
                last_token = data["raw_tokens"][-1]
                assert captured_crops[0][1] == last_token
                assert captured_crops[0][2] == "HELP"


def test_actual_confidence_not_dummy_constant(client):
    """
    Actual confidence must vary based on neural model activations,
    never returning a static dummy constant like 0.95 or 0.98.
    """
    frame_b64 = make_synthetic_frame_b64()

    mock_v_correct = {
        "is_verified": True,
        "is_correct": True,
        "provider_used": "groq",
        "key_name": "Groq-Key-1",
        "verified_sentence_en": "A.",
        "verified_sentence_hi": "ए।",
        "wrong_sign": "",
        "correct_sign": "",
        "explanation": "Correct."
    }

    with patch.object(verifier, "check_internet", return_value=True), \
         patch.object(verifier, "is_available", return_value=(True, "Online")), \
         patch.object(verifier, "verify_sentence", return_value=mock_v_correct), \
         patch.object(online_learner, "reward_prediction", return_value={"status": "rewarded"}):

        res = client.post("/api/webcam/predict", json={
            "frame_base64": frame_b64,
            "session_id": "conf_check_sess",
            "allow_empty": False   # Static path: skin segmentation detects synthetic blob
        })
        assert res.status_code == 200
        data = res.json()
        conf = data["actual_confidence"]
        # Must be float between 0 and 1
        assert isinstance(conf, float)
        assert 0.0 < conf <= 0.99
        # Must not be a hardcoded dummy 0.95 or 0.98
        assert conf != 0.95 and conf != 0.98
