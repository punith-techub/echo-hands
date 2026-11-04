"""
Unit tests to verify 100% accuracy on real Indian Sign Language (ISL) hand alphabet crops.
Ensures no bias towards 'I', 'J', 'K', or '9' and verifies high prototype similarity.
"""

import os
import cv2
import pytest
from CORE.vision import DualBrainVisionEngine

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "isl_hand_samples")

@pytest.fixture(scope="module")
def vision_engine():
    return DualBrainVisionEngine()

@pytest.mark.parametrize("letter", list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
def test_all_26_isl_alphabets_recognized(vision_engine, letter):
    sample_path = os.path.join(DATA_DIR, f"{letter}.png")
    assert os.path.exists(sample_path), f"Missing hand sample crop for letter {letter}"
    
    img = cv2.imread(sample_path)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    res = vision_engine.predict_sign(rgb)
    predicted = res["predicted_sign"]
    confidence = res["confidence"]
    
    assert predicted == letter, (
        f"ISL Letter {letter} was misclassified as '{predicted}' with confidence {confidence:.2f}"
    )
    assert confidence >= 0.70, f"Confidence for letter {letter} too low: {confidence:.2f}"
