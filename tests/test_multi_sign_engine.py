"""
Unit tests for CORE.multi_sign_engine
"""
import pytest
import numpy as np
import cv2
from PIL import Image
from CORE.multi_sign_engine import MultiSignEngine, SignRegion

@pytest.fixture
def engine():
    return MultiSignEngine(target_size=(224, 224))

def test_engine_initialization(engine):
    assert engine.target_size == (224, 224)
    assert engine.padding_ratio > 0

def test_fallback_on_blank_image(engine):
    # Completely black image
    blank = np.zeros((300, 300, 3), dtype=np.uint8)
    regions = engine.extract_signs(blank)
    assert len(regions) == 1
    assert regions[0].crop.shape == (224, 224, 3)
    assert regions[0].index == 0

def test_skin_segmentation(engine):
    # Image with skin patch in center
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    # Wheatish skin in BGR: (130, 165, 215)
    cv2.circle(img, (100, 100), 40, (130, 165, 215), -1)
    mask = engine.segment_skin(img)
    assert mask.shape == (200, 200)
    assert np.sum(mask > 0) > 100

def test_dual_hand_merging(engine):
    # Two hands side by side in close proximity
    img_w, img_h = 600, 400
    box_a = (150, 150, 60, 80)
    box_b = (220, 160, 60, 80)
    merged = engine._merge_dual_hands([box_a, box_b], img_w, img_h)
    # Should merge into single envelope
    assert len(merged) == 1
    mx, my, mw, mh, is_dual = merged[0]
    assert is_dual is True
    assert mx <= 150
    assert mx + mw >= 280

def test_reading_order_sorting(engine):
    # Grid of 4 bounding boxes:
    # Top-Left, Top-Right, Bottom-Left, Bottom-Right
    boxes = [
        (300, 250, 50, 50, False),  # Bottom-Right
        (50, 50, 50, 50, False),    # Top-Left
        (300, 50, 50, 50, False),   # Top-Right
        (50, 250, 50, 50, False),   # Bottom-Left
    ]
    sorted_boxes = engine._sort_reading_order(boxes, img_h=400)
    assert len(sorted_boxes) == 4
    # Expected order: Top-Left, Top-Right, Bottom-Left, Bottom-Right
    assert sorted_boxes[0][0] == 50 and sorted_boxes[0][1] == 50
    assert sorted_boxes[1][0] == 300 and sorted_boxes[1][1] == 50
    assert sorted_boxes[2][0] == 50 and sorted_boxes[2][1] == 250
    assert sorted_boxes[3][0] == 300 and sorted_boxes[3][1] == 250

def test_crop_square_normalized(engine):
    rgb = np.zeros((400, 600, 3), dtype=np.uint8)
    crop = engine._crop_square_normalized(rgb, (100, 100, 80, 120))
    assert crop.shape == (224, 224, 3)
    assert crop.dtype == np.uint8

def test_door_and_boundary_rejection_in_webcam_mode(engine):
    # Create image simulating background wooden door touching top of frame
    img = np.ones((480, 640, 3), dtype=np.uint8) * 30
    cv2.rectangle(img, (150, 0), (320, 380), (50, 110, 190), -1)
    regions = engine.extract_signs(img, allow_empty=True)
    # Background door touching top border must be rejected
    assert len(regions) == 0

def test_face_masking_prevents_face_classification(engine):
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    mask = np.ones((480, 640), dtype=np.uint8) * 255
    if engine.face_detector is not None:
        masked = engine.detect_and_mask_faces(img, mask)
        assert masked.shape == (480, 640)

def test_pil_image_input(engine):
    pil_img = Image.new("RGB", (300, 300), color=(50, 50, 50))
    regions = engine.extract_signs(pil_img)
    assert len(regions) >= 1
    assert regions[0].crop.shape == (224, 224, 3)
