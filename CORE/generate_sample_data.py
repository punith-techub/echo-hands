"""
ECHOHANDS - Sample Test Image Generator
Generates realistic benchmark images for single letters, word gestures,
and multi-sign strips (C-A-T, H-E-L-P, I-NEED-FOOD) in data/ directory.
"""

import os
import cv2
import numpy as np
import math
from CORE.train import render_gesture_glyph, SKIN_TONES

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

from CORE.isl_trainer import render_word_glyph

def create_single_gesture(class_name: str, filename: str, skin_tone=SKIN_TONES[1]):
    """Create a single isolated sign image (224x224)."""
    img = render_gesture_glyph(class_name, skin_tone, size=224, seed=101)
    # Convert RGB to BGR for saving with cv2
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    path = os.path.join(DATA_DIR, filename)
    cv2.imwrite(path, bgr)
    print(f"Generated single gesture: {path}")

def create_word_gesture(word_name: str, filename: str):
    """Create dual-hand word gesture image (224x224)."""
    rgb = render_word_glyph(word_name, size=224, seed=sum(ord(c) for c in word_name))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    path = os.path.join(DATA_DIR, filename)
    cv2.imwrite(path, bgr)
    print(f"Generated word gesture: {path}")

def create_horizontal_strip(classes_list, filename: str):
    """
    Create a horizontal multi-sign image with multiple signs arranged
    left-to-right on a realistic neutral surface.
    """
    card_h = 260
    card_w = 224
    gap = 40
    margin = 50
    total_w = margin * 2 + len(classes_list) * card_w + (len(classes_list) - 1) * gap
    total_h = card_h + margin * 2

    # Background canvas
    canvas = np.ones((total_h, total_w, 3), dtype=np.uint8) * 28
    # Subtle studio shadow / floor line
    cv2.line(canvas, (0, total_h - 15), (total_w, total_h - 15), (20, 20, 20), 2)

    for i, cls in enumerate(classes_list):
        tone = SKIN_TONES[(i + 1) % len(SKIN_TONES)]
        glyph = render_gesture_glyph(cls, tone, size=card_w, seed=i * 55 + 17)
        # Convert glyph to BGR
        glyph_bgr = cv2.cvtColor(glyph, cv2.COLOR_RGB2BGR)

        # Place onto canvas
        x_offset = margin + i * (card_w + gap)
        y_offset = margin + (card_h - card_w) // 2

        # Subregion placement
        canvas[y_offset:y_offset + card_w, x_offset:x_offset + card_w] = glyph_bgr

    path = os.path.join(DATA_DIR, filename)
    cv2.imwrite(path, canvas)
    print(f"Generated multi-sign strip ({len(classes_list)} signs): {path}")

def generate_all_samples():
    print("Generating comprehensive test dataset in data/...")
    # 1. Single Alphanumerics
    create_single_gesture("A", "sample_letter_a.png")
    create_single_gesture("5", "sample_number_5.png")

    # 2. Words
    create_word_gesture("NAMASTE", "sample_namaste.png")
    create_word_gesture("HELP", "sample_help.png")

    # 3. Multi-Sign Strips
    create_horizontal_strip(["C", "A", "T"], "sample_strip_cat.png")
    create_horizontal_strip(["H", "E", "L", "P"], "sample_strip_help.png")
    create_horizontal_strip(["I", "N", "E", "E", "D", "F", "O", "O", "D"], "sample_sentence_food.png")

    print("All sample test images generated successfully!")

if __name__ == "__main__":
    generate_all_samples()
