"""
Unit tests for CORE.vision
"""
import pytest
import numpy as np
import torch
from CORE.vision import DualBrainVisionEngine, GradCAM
from CORE.model_arch import ISLNet

@pytest.fixture
def vision_engine():
    return DualBrainVisionEngine()

def test_vision_engine_init(vision_engine):
    assert vision_engine.model is not None
    assert vision_engine.memory is not None
    assert vision_engine.grad_cam is not None

def test_preprocess_tensor(vision_engine):
    dummy_crop = np.zeros((224, 224, 3), dtype=np.uint8)
    tensor = vision_engine.preprocess_tensor(dummy_crop)
    assert tensor.shape == (1, 3, 224, 224)
    assert tensor.device == vision_engine.device

def test_predict_sign_structure(vision_engine):
    dummy_crop = np.random.randint(50, 200, (224, 224, 3), dtype=np.uint8)
    res = vision_engine.predict_sign(dummy_crop, is_dual_hand=False)
    
    assert "predicted_sign" in res
    assert "confidence" in res
    assert "decision_margin" in res
    assert "chosen_brain" in res
    assert "top_candidates" in res
    assert "gradcam_heatmap" in res
    assert len(res["top_candidates"]) > 0
    assert 0.0 <= res["confidence"] <= 1.0

def test_gradcam_generation(vision_engine):
    dummy_crop = np.random.randint(50, 200, (224, 224, 3), dtype=np.uint8)
    tensor = vision_engine.preprocess_tensor(dummy_crop)
    tensor.requires_grad = True
    cam_map = vision_engine.grad_cam.generate_heatmap(tensor, target_class_idx=0)
    assert cam_map.shape == (224, 224)
    assert np.max(cam_map) <= 1.0
    assert np.min(cam_map) >= 0.0

def test_forced_brain_mode(vision_engine):
    dummy_crop = np.random.randint(50, 200, (224, 224, 3), dtype=np.uint8)
    res_word = vision_engine.predict_sign(dummy_crop, preferred_brain="word")
    assert res_word["sign_type"] == "word"
    assert "Brain-2" in res_word["chosen_brain"]
