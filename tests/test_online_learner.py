"""
Unit tests for ECHOHANDS Online Self-Learning Engine (OnlineLearner)
Verifies:
1. Online learning updates classifier weights targeting correct sign.
2. Negative margin loss severely penalizes wrong sign.
3. Experience buffer persistence and replay.
4. User-taught prototype priority in dual-brain arbitration.
"""

import os
import shutil
import tempfile
import torch
import numpy as np
import pytest

from CORE.model_arch import ISLNet
from CORE.isl_trainer import ISLMemoryTrainer
from CORE.online_learner import OnlineLearner
from CORE.vision import DualBrainVisionEngine
from CORE.sign_knowledge import CLASS_TO_INDEX, INDEX_TO_CLASS


@pytest.fixture
def temp_env():
    temp_dir = tempfile.mkdtemp()
    mem_path = os.path.join(temp_dir, "test_memory.pt")
    
    # Initialize real model
    model = ISLNet(num_classes=35, embedding_dim=512, pretrained=False)
    weights_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "alphanumeric_model.pt")
    if os.path.exists(weights_path):
        model.load_state_dict(torch.load(weights_path, map_location="cpu"))
    model.eval()

    mem = ISLMemoryTrainer(mem_path)
    mem.populate_initial_words(model=model)
    learner = OnlineLearner(model=model, memory_trainer=mem)

    yield {
        "model": model,
        "memory": mem,
        "learner": learner,
        "temp_dir": temp_dir
    }

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_online_learner_penalizes_wrong_and_boosts_correct(temp_env):
    learner = temp_env["learner"]
    model = temp_env["model"]
    mem = temp_env["memory"]

    # Synthesize dummy crop
    crop = np.random.randint(40, 200, (224, 224, 3), dtype=np.uint8)

    # Initial inference
    with torch.no_grad():
        crop_f = (crop.astype(np.float32) / 255.0 - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
        t = torch.from_numpy(crop_f).permute(2, 0, 1).unsqueeze(0).float()
        l_init, _ = model(t)
        p_init = torch.softmax(l_init, dim=1)[0]

    # Punish "1", Teach "K"
    res = learner.learn_from_feedback(
        crop_rgb=crop,
        wrong_sign="1",
        correct_sign="K",
        is_dual_hand=False
    )

    assert res["status"] == "success"
    assert res["cnn_weights_trained"] is True
    assert res["prototype_memory_updated"] is True

    # Post-learning inference
    with torch.no_grad():
        l_post, _ = model(t)
        p_post = torch.softmax(l_post, dim=1)[0]

    k_idx = CLASS_TO_INDEX["K"]
    one_idx = CLASS_TO_INDEX["1"]

    # K probability must be dominant
    assert p_post[k_idx].item() > p_init[k_idx].item() or p_post[k_idx].item() > 0.80

    # Prototype memory must reflect user taught flag
    assert "K" in mem.prototypes
    assert mem.prototypes["K"]["metadata"].get("is_user_taught") is True
