"""
Integration tests for FastAPI endpoints in CORE.app
"""
import pytest
import io
import numpy as np
import cv2
from PIL import Image
from fastapi.testclient import TestClient
from CORE.app import app

@pytest.fixture
def client():
    import shutil
    import os
    memory_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "isl_memory.pt")
    backup_path = memory_path + ".bak"
    if os.path.exists(memory_path):
        shutil.copyfile(memory_path, backup_path)
    try:
        yield TestClient(app)
    finally:
        if os.path.exists(backup_path):
            shutil.copyfile(backup_path, memory_path)
            os.remove(backup_path)
            from CORE.app import vision_engine
            vision_engine.memory.load_or_initialize()

def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["alphanumeric_classes"] == 35
    assert data["prototype_memory_words"] >= 50

def test_vocabulary_endpoint(client):
    response = client.get("/api/vocabulary")
    assert response.status_code == 200
    data = response.json()
    assert len(data["alphanumerics"]) == 35
    assert len(data["words"]) >= 50

def test_sample_images_endpoint(client):
    response = client.get("/api/sample-images")
    assert response.status_code == 200
    data = response.json()
    assert "samples" in data

def test_predict_endpoint_with_synthetic_image(client):
    # Create simple in-memory PNG image
    img = np.ones((224, 224, 3), dtype=np.uint8) * 50
    # Add a hand-like patch
    cv2.circle(img, (112, 112), 40, (130, 165, 215), -1)
    pil_img = Image.fromarray(img)
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)

    response = client.post(
        "/api/predict",
        files={"file": ("test_gesture.png", buf.getvalue(), "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "regions" in data
    assert "sentence" in data
    assert "speech" in data
    assert len(data["regions"]) >= 1

def test_learn_endpoint(client):
    img = np.ones((224, 224, 3), dtype=np.uint8) * 80
    pil_img = Image.fromarray(img)
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)

    try:
        response = client.post(
            "/api/learn",
            data={"word": "CUSTOM_SIGN", "category": "action"},
            files={"file": ("custom_gesture.png", buf.getvalue(), "image/png")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["word"] == "CUSTOM_SIGN"
        assert data["total_prototypes"] > 0
    finally:
        from CORE.app import vision_engine
        vision_engine.memory.remove_prototype("CUSTOM_SIGN")
        vision_engine.memory.save()

def test_root_serves_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Echo" in response.text or "ECHOHANDS" in response.text

def test_metrics_endpoint(client):
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "overall_accuracy" in data
    assert "confusion_matrix_url" in data
    assert "roc_curve_url" in data

def test_metrics_images(client):
    cm_resp = client.get("/api/metrics/confusion-matrix")
    assert cm_resp.status_code == 200
    assert cm_resp.headers["content-type"] == "image/png"

    roc_resp = client.get("/api/metrics/roc-curve")
    assert roc_resp.status_code == 200
    assert roc_resp.headers["content-type"] == "image/png"

@pytest.mark.parametrize("sample_name", [
    "sample_letter_a.png",
    "sample_number_5.png",
    "sample_namaste.png",
    "sample_help.png",
    "sample_strip_cat.png",
    "sample_strip_help.png",
    "sample_sentence_food.png"
])
def test_all_sample_images_predict(client, sample_name):
    import os
    sample_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", sample_name)
    assert os.path.exists(sample_path)
    with open(sample_path, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/predict",
        files={"file": (sample_name, file_bytes, "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["regions_count"] >= 1
    assert len(data["regions"]) == data["regions_count"]
    assert "english_sentence" in data["sentence"]
    assert "hindi_sentence" in data["sentence"]
    assert "waveform_pattern" in data["speech"]
    assert len(data["speech"]["waveform_pattern"]) == 32

def test_feedback_thumbs_up_reward(client):
    # Predict first to get crop_base64
    img = np.ones((224, 224, 3), dtype=np.uint8) * 128
    _, buf = cv2.imencode(".jpg", img)
    
    pred_res = client.post(
        "/api/predict",
        files={"file": ("test.jpg", buf.tobytes(), "image/jpeg")}
    )
    assert pred_res.status_code == 200
    pred_data = pred_res.json()
    crop_b64 = pred_data["regions"][0]["crop_base64"]
    predicted_sign = pred_data["regions"][0]["predicted_sign"]

    # Submit Thumbs Up
    fb_res = client.post(
        "/api/feedback",
        json={
            "is_positive": True,
            "predicted_sign": predicted_sign,
            "crop_base64": crop_b64
        }
    )
    assert fb_res.status_code == 200
    fb_data = fb_res.json()
    assert fb_data["status"] == "success"
    assert fb_data["action"] == "reward"
    assert "reinforced" in fb_data["message"]

def test_feedback_thumbs_down_punish_and_correct(client):
    # Create test image
    img = np.ones((224, 224, 3), dtype=np.uint8) * 128
    _, buf = cv2.imencode(".jpg", img)
    
    pred_res = client.post(
        "/api/predict",
        files={"file": ("test.jpg", buf.tobytes(), "image/jpeg")}
    )
    assert pred_res.status_code == 200
    pred_data = pred_res.json()
    crop_b64 = pred_data["regions"][0]["crop_base64"]
    predicted_sign = pred_data["regions"][0]["predicted_sign"]

    # Submit Thumbs Down with correction
    fb_res = client.post(
        "/api/feedback",
        json={
            "is_positive": False,
            "predicted_sign": predicted_sign,
            "correct_sign": "NAMASTE",
            "crop_base64": crop_b64
        }
    )
    assert fb_res.status_code == 200
    fb_data = fb_res.json()
    assert fb_data["status"] == "success"
    assert fb_data["action"] == "punished_and_corrected"
    assert fb_data["previous_sign"] == predicted_sign.upper()
    assert fb_data["corrected_sign"] == "NAMASTE"
    assert "updated_prediction" in fb_data

def test_text_to_isl_endpoint(client):
    res = client.post("/api/text-to-isl", json={"text": "Please help me"})
    assert res.status_code == 200
    data = res.json()
    assert "HELP" in data["isl_tokens"]
    assert len(data["animation_sequence"]) > 0

def test_download_extension_endpoint(client):
    res = client.get("/api/download-extension")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert len(res.content) > 1000

def test_crx_install_endpoint(client):
    res = client.get("/echo-hands.crx")
    assert res.status_code == 200
    assert "chrome-extension" in res.headers["content-type"]
    assert len(res.content) > 1000



