"""
Unit tests for CORE.isl_trainer
"""
import pytest
import os
import torch
import numpy as np
from CORE.isl_trainer import ISLMemoryTrainer

@pytest.fixture
def temp_memory(tmp_path):
    mem_file = os.path.join(tmp_path, "test_isl_memory.pt")
    trainer = ISLMemoryTrainer(memory_path=mem_file, feature_dim=512)
    return trainer

def test_initial_prototypes_count(temp_memory):
    count = temp_memory.count()
    # Pre-seeded ISL words should be >= 50
    assert count >= 50
    assert "NAMASTE" in temp_memory.prototypes
    assert "HELP" in temp_memory.prototypes

def test_add_prototype_and_match(temp_memory):
    # Create random feature vector
    vec = torch.randn(512)
    temp_memory.add_prototype("TEST_GESTURE", vec, metadata={"category": "test"})
    assert "TEST_GESTURE" in temp_memory.prototypes

    # Query with the exact same vector
    matches = temp_memory.match(vec, top_k=3)
    assert len(matches) > 0
    top_word, top_sim, meta = matches[0]
    assert top_word == "TEST_GESTURE"
    # Cosine similarity of identical vector should be ~1.0
    assert pytest.approx(top_sim, abs=1e-4) == 1.0
    assert meta.get("category") == "test"

def test_persistence(temp_memory, tmp_path):
    vec = torch.randn(512)
    temp_memory.add_prototype("PERSIST_WORD", vec)
    save_path = os.path.join(tmp_path, "persisted_memory.pt")
    temp_memory.save(save_path)
    assert os.path.exists(save_path)

    # Load in new instance
    loaded = ISLMemoryTrainer(memory_path=save_path, feature_dim=512)
    assert "PERSIST_WORD" in loaded.prototypes
    assert loaded.count() == temp_memory.count()

def test_remove_prototype(temp_memory):
    assert temp_memory.remove_prototype("NAMASTE") is True
    assert "NAMASTE" not in temp_memory.prototypes
    assert temp_memory.remove_prototype("NON_EXISTENT") is False

def test_reward_prediction(temp_memory):
    vec = torch.randn(512)
    # Add initial gesture
    temp_memory.add_prototype("REWARD_TEST", vec)
    old_samples = temp_memory.prototypes["REWARD_TEST"]["samples"]

    # Reward with a slightly perturbed vector
    pert = vec + torch.randn(512) * 0.1
    res = temp_memory.reward_prediction("REWARD_TEST", pert)
    assert res["status"] == "rewarded"
    assert res["samples"] == old_samples + 1
    assert "new_similarity" in res

def test_punish_and_correct(temp_memory):
    feature = torch.randn(512)
    temp_memory.add_prototype("FALSE_CLASS", feature)
    temp_memory.add_prototype("TRUE_CLASS", -feature)

    # False class matches with high similarity
    matches_before = temp_memory.match(feature, top_k=2)
    assert matches_before[0][0] == "FALSE_CLASS"

    # Punish false class and correct to true class
    res = temp_memory.punish_and_correct(
        wrong_word="FALSE_CLASS",
        correct_word="TRUE_CLASS",
        feature_vector=feature,
        punishment_factor=0.8
    )
    assert res["status"] == "punished_and_corrected"
    assert res["wrong_word"] == "FALSE_CLASS"
    assert res["correct_word"] == "TRUE_CLASS"

    # Query again with same feature - TRUE_CLASS should now have significantly higher similarity!
    matches_after = temp_memory.match(feature, top_k=2)
    assert matches_after[0][0] == "TRUE_CLASS"

