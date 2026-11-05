"""
Tests for ISL Landmark Classifier (CORE/isl_landmarks.py)
Verifies authentic Two-Handed and One-Handed ISL recognition.
"""

from types import SimpleNamespace
from CORE.isl_landmarks import classify_isl_landmarks

def make_landmark(x, y, z=0.0):
    return SimpleNamespace(x=x, y=y, z=z)

def make_hand(wrist=(0.5, 0.8), ext_fingers=(False, False, False, False, False)):
    """
    Creates 21 mock landmarks.
    ext_fingers: (thumb, index, middle, ring, pinky)
    """
    wx, wy = wrist
    lms = [make_landmark(wx, wy)]
    
    # Thumb 1-4
    t_ext = ext_fingers[0]
    lms.extend([
        make_landmark(wx - 0.05, wy - 0.05),
        make_landmark(wx - 0.10, wy - 0.10),
        make_landmark(wx - 0.14, wy - 0.15),
        make_landmark(wx - 0.20 if t_ext else wx - 0.08, wy - 0.22 if t_ext else wy - 0.09)
    ])
    
    # Index 5-8
    i_ext = ext_fingers[1]
    lms.extend([
        make_landmark(wx - 0.04, wy - 0.20),
        make_landmark(wx - 0.04, wy - 0.30),
        make_landmark(wx - 0.04, wy - 0.38),
        make_landmark(wx - 0.04, wy - 0.50 if i_ext else wy - 0.25)
    ])
    
    # Middle 9-12
    m_ext = ext_fingers[2]
    lms.extend([
        make_landmark(wx, wy - 0.21),
        make_landmark(wx, wy - 0.31),
        make_landmark(wx, wy - 0.40),
        make_landmark(wx, wy - 0.53 if m_ext else wy - 0.25)
    ])
    
    # Ring 13-16
    r_ext = ext_fingers[3]
    lms.extend([
        make_landmark(wx + 0.04, wy - 0.20),
        make_landmark(wx + 0.04, wy - 0.30),
        make_landmark(wx + 0.04, wy - 0.38),
        make_landmark(wx + 0.04, wy - 0.50 if r_ext else wy - 0.25)
    ])
    
    # Pinky 17-20
    p_ext = ext_fingers[4]
    lms.extend([
        make_landmark(wx + 0.08, wy - 0.18),
        make_landmark(wx + 0.08, wy - 0.26),
        make_landmark(wx + 0.08, wy - 0.34),
        make_landmark(wx + 0.08, wy - 0.45 if p_ext else wy - 0.23)
    ])
    
    return lms

def test_single_hand_v_sign():
    hand = make_hand(ext_fingers=(False, True, True, False, False))
    res = classify_isl_landmarks([hand])
    assert res is not None
    assert res["sign"] == "V"
    assert res["confidence"] >= 0.90
    assert res["handedness"] == "one-handed"

def test_single_hand_w_sign():
    hand = make_hand(ext_fingers=(False, True, True, True, False))
    res = classify_isl_landmarks([hand])
    assert res is not None
    assert res["sign"] == "W"
    assert res["confidence"] >= 0.90

def test_single_hand_d_sign():
    hand = make_hand(ext_fingers=(False, True, False, False, False))
    res = classify_isl_landmarks([hand])
    assert res is not None
    assert res["sign"] == "D"

def test_two_handed_namaste():
    # Two hands open facing each other closely
    h1 = make_hand(wrist=(0.46, 0.7), ext_fingers=(True, True, True, True, True))
    h2 = make_hand(wrist=(0.54, 0.7), ext_fingers=(True, True, True, True, True))
    res = classify_isl_landmarks([h1, h2])
    assert res is not None
    assert res["sign"] == "NAMASTE"
    assert res["handedness"] == "two-handed"

def test_two_handed_g_fists():
    # Two fists stacked vertically
    h_lower = make_hand(wrist=(0.5, 0.75), ext_fingers=(False, False, False, False, False))
    h_upper = make_hand(wrist=(0.5, 0.45), ext_fingers=(False, False, False, False, False))
    res = classify_isl_landmarks([h_lower, h_upper])
    assert res is not None
    assert res["sign"] == "G"
    assert res["handedness"] == "two-handed"

def test_two_handed_a_letter():
    # Left hand open, right hand index touching left thumb
    # Thumb tip of left hand is at (0.30, 0.48)
    h_left = make_hand(wrist=(0.40, 0.70), ext_fingers=(True, True, True, True, True))
    # Right hand with index touching left thumb tip
    h_right = make_hand(wrist=(0.55, 0.70), ext_fingers=(False, True, False, False, False))
    # Position right index tip right at left thumb tip
    h_right[8] = make_landmark(h_left[4].x + 0.01, h_left[4].y + 0.01)
    res = classify_isl_landmarks([h_left, h_right])
    assert res is not None
    assert res["sign"] == "A"
    assert res["handedness"] == "two-handed"

def test_two_handed_x_cross():
    # Both index fingers extended crossing each other
    h1 = make_hand(wrist=(0.45, 0.70), ext_fingers=(False, True, False, False, False))
    h2 = make_hand(wrist=(0.55, 0.70), ext_fingers=(False, True, False, False, False))
    h2[8] = make_landmark(h1[8].x + 0.02, h1[8].y + 0.02)
    res = classify_isl_landmarks([h1, h2])
    assert res is not None
    assert res["sign"] == "X"
    assert res["handedness"] == "two-handed"

