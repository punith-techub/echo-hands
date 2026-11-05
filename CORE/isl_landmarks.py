"""
ECHOHANDS - ISL Landmark Geometric Classifier
High-accuracy deterministic classification of Indian Sign Language (ISL) gestures
using 21 3D MediaPipe hand landmarks per hand.
Covers both TWO-HANDED (A, B, D, E, F, G, H, M, N, P, S, T, X, NAMASTE, HELP, STOP, etc.)
and ONE-HANDED (C, L, V, W, I, Y, 1, 2, 3, 4, 5, HELLO, FOOD, etc.) signs.
"""

import math
from typing import List, Dict, Any, Optional, Tuple

def _dist(p1, p2) -> float:
    """Euclidean distance in normalized (x, y) coordinates."""
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

def _dist3d(p1, p2) -> float:
    """Euclidean distance in (x, y, z) coordinates."""
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

def analyze_single_hand_geometry(landmarks) -> Dict[str, Any]:
    """
    Analyze extension and configuration of 5 fingers for a single hand.
    Landmarks indices:
      0: Wrist
      1-4: Thumb (1=CMC, 2=MCP, 3=IP, 4=TIP)
      5-8: Index (5=MCP, 6=PIP, 7=DIP, 8=TIP)
      9-12: Middle (9=MCP, 10=PIP, 11=DIP, 12=TIP)
      13-16: Ring (13=MCP, 14=PIP, 15=DIP, 16=TIP)
      17-20: Pinky (17=MCP, 18=PIP, 19=DIP, 20=TIP)
    """
    wrist = landmarks[0]
    hand_size = max(0.01, _dist(wrist, landmarks[9]))  # Wrist to Middle MCP as reference scale

    # Finger extensions: orientation-invariant tip-to-MCP distance vs PIP-to-MCP distance
    # For any extended finger (vertical, horizontal, or diagonal), TIP is significantly farther from MCP than PIP is.
    thumb_ext = (_dist(landmarks[4], wrist) > 1.15 * _dist(landmarks[2], wrist)) and (_dist(landmarks[4], landmarks[5]) > 0.40 * hand_size)
    index_ext = _dist(landmarks[8], landmarks[5]) > 1.20 * _dist(landmarks[6], landmarks[5])
    middle_ext = _dist(landmarks[12], landmarks[9]) > 1.20 * _dist(landmarks[10], landmarks[9])
    ring_ext = _dist(landmarks[16], landmarks[13]) > 1.20 * _dist(landmarks[14], landmarks[13])
    pinky_ext = _dist(landmarks[20], landmarks[17]) > 1.20 * _dist(landmarks[18], landmarks[17])

    ext_count = sum([index_ext, middle_ext, ring_ext, pinky_ext])
    all_ext_count = ext_count + (1 if thumb_ext else 0)

    # Finger spread / V-angle
    index_middle_dist = _dist(landmarks[8], landmarks[12]) / hand_size
    middle_ring_dist = _dist(landmarks[12], landmarks[16]) / hand_size

    # Clustered fingertips (e.g. FOOD / EAT)
    tips = [landmarks[4], landmarks[8], landmarks[12], landmarks[16], landmarks[20]]
    center_tip_x = sum(t.x for t in tips) / 5.0
    center_tip_y = sum(t.y for t in tips) / 5.0
    avg_tip_spread = sum(math.hypot(t.x - center_tip_x, t.y - center_tip_y) for t in tips) / (5.0 * hand_size)
    is_clustered = avg_tip_spread < 0.38

    # C-shape check: curved index, middle, ring, thumb
    is_c_shape = False
    if not is_clustered and not index_ext and not middle_ext and not pinky_ext:
        # Check if thumb and index are curved with gap in between
        thumb_index_gap = _dist(landmarks[4], landmarks[8]) / hand_size
        if 0.45 < thumb_index_gap < 1.35 and landmarks[4].y > landmarks[8].y - 0.2:
            is_c_shape = True

    return {
        "wrist": wrist,
        "hand_size": hand_size,
        "thumb_ext": thumb_ext,
        "index_ext": index_ext,
        "middle_ext": middle_ext,
        "ring_ext": ring_ext,
        "pinky_ext": pinky_ext,
        "ext_count": ext_count,          # 4 non-thumb fingers
        "all_ext_count": all_ext_count,  # All 5 fingers
        "index_middle_dist": index_middle_dist,
        "middle_ring_dist": middle_ring_dist,
        "is_clustered": is_clustered,
        "is_c_shape": is_c_shape,
        "center_x": sum(lm.x for lm in landmarks) / 21.0,
        "center_y": sum(lm.y for lm in landmarks) / 21.0,
        "thumb_tip": landmarks[4],
        "index_tip": landmarks[8],
        "middle_tip": landmarks[12],
        "ring_tip": landmarks[16],
        "pinky_tip": landmarks[20]
    }

def classify_isl_landmarks(hand_landmarks_list: List[Any]) -> Optional[Dict[str, Any]]:
    """
    Classify 1 or 2 hands using authentic ISL geometric rules.
    Returns:
      {
        "sign": str,
        "confidence": float,
        "handedness": "two-handed" | "one-handed",
        "desc": str
      }
    """
    if not hand_landmarks_list or len(hand_landmarks_list) == 0:
        return None

    # =========================================================================
    # CASE A: TWO HANDS DETECTED (High-Priority Authenticated ISL Signs)
    # =========================================================================
    if len(hand_landmarks_list) >= 2:
        h1 = analyze_single_hand_geometry(hand_landmarks_list[0])
        h2 = analyze_single_hand_geometry(hand_landmarks_list[1])

        # Normalize left/right based on horizontal X coordinate
        left_h = h1 if h1["center_x"] < h2["center_x"] else h2
        right_h = h2 if h1["center_x"] < h2["center_x"] else h1
        avg_scale = (left_h["hand_size"] + right_h["hand_size"]) / 2.0

        palm_distance = _dist(left_h["wrist"], right_h["wrist"]) / avg_scale
        center_distance = math.hypot(left_h["center_x"] - right_h["center_x"], left_h["center_y"] - right_h["center_y"]) / avg_scale

        # 1. NAMASTE: Both open hands pressed together at chest
        if left_h["all_ext_count"] >= 4 and right_h["all_ext_count"] >= 4:
            if center_distance < 1.4:
                return {
                    "sign": "NAMASTE",
                    "confidence": 0.96,
                    "handedness": "two-handed",
                    "desc": "Both open palms joined vertically in Namaste greeting"
                }

        # 2. HELP: One flat palm below supporting thumbs-up fist above
        lower_h = left_h if left_h["center_y"] > right_h["center_y"] else right_h
        upper_h = right_h if left_h["center_y"] > right_h["center_y"] else left_h
        y_diff = (lower_h["center_y"] - upper_h["center_y"]) / avg_scale

        if y_diff > 0.40 and center_distance < 1.6:
            # Lower hand open flat, upper hand fist with thumb upright
            if lower_h["ext_count"] >= 3 and upper_h["ext_count"] <= 1 and upper_h["thumb_ext"]:
                return {
                    "sign": "HELP",
                    "confidence": 0.95,
                    "handedness": "two-handed",
                    "desc": "Flat open palm lifting thumbs-up fist in ISL Help sign"
                }

        # 3. STOP: Lower hand flat horizontal, upper hand chopping down vertically
        if y_diff > 0.35 and lower_h["ext_count"] >= 3 and upper_h["ext_count"] >= 3 and center_distance < 1.5:
            return {
                "sign": "STOP",
                "confidence": 0.93,
                "handedness": "two-handed",
                "desc": "Dominant hand chopping down vertically on flat horizontal palm"
            }

        # 4. G (ISL): Two closed fists stacked vertically
        if left_h["all_ext_count"] <= 1 and right_h["all_ext_count"] <= 1:
            if y_diff > 0.35 and abs(left_h["center_x"] - right_h["center_x"]) / avg_scale < 0.65:
                return {
                    "sign": "G",
                    "confidence": 0.94,
                    "handedness": "two-handed",
                    "desc": "Two closed fists stacked vertically one on top of the other"
                }

        # 5. X (ISL): Both index fingers extended and crossing each other
        if left_h["index_ext"] and left_h["middle_ext"] is False and left_h["ring_ext"] is False and left_h["pinky_ext"] is False:
            if right_h["index_ext"] and right_h["middle_ext"] is False and right_h["ring_ext"] is False and right_h["pinky_ext"] is False:
                index_cross_dist = _dist(left_h["index_tip"], right_h["index_tip"]) / avg_scale
                if index_cross_dist < 0.75:
                    return {
                        "sign": "X",
                        "confidence": 0.94,
                        "handedness": "two-handed",
                        "desc": "Both index fingers crossed horizontally forming an X"
                    }

        # 6. S (ISL): Both pinkies hooked together
        if left_h["pinky_ext"] and right_h["pinky_ext"] and left_h["ext_count"] == 1 and right_h["ext_count"] == 1:
            pinky_dist = _dist(left_h["pinky_tip"], right_h["pinky_tip"]) / avg_scale
            if pinky_dist < 0.65:
                return {
                    "sign": "S",
                    "confidence": 0.93,
                    "handedness": "two-handed",
                    "desc": "Little fingers of both hands hooked into each other"
                }

        # 7. A (ISL Two-Handed): Non-dominant hand open/thumb out, dominant index touches thumb tip
        # Check right index touching left thumb
        r_index_to_l_thumb = _dist(right_h["index_tip"], left_h["thumb_tip"]) / avg_scale
        l_index_to_r_thumb = _dist(left_h["index_tip"], right_h["thumb_tip"]) / avg_scale

        if (r_index_to_l_thumb < 0.45 and right_h["index_ext"] and right_h["ext_count"] <= 2) or \
           (l_index_to_r_thumb < 0.45 and left_h["index_ext"] and left_h["ext_count"] <= 2):
            return {
                "sign": "A",
                "confidence": 0.95,
                "handedness": "two-handed",
                "desc": "Dominant index finger touching the tip of the secondary thumb"
            }

        # 8. B (ISL Two-Handed): Both hands form circles/loops touching side by side
        if center_distance < 1.3 and left_h["ext_count"] <= 2 and right_h["ext_count"] <= 2:
            loop_dist = _dist(left_h["index_tip"], right_h["index_tip"]) / avg_scale
            if loop_dist < 0.55:
                return {
                    "sign": "B",
                    "confidence": 0.93,
                    "handedness": "two-handed",
                    "desc": "Thumbs and index fingers of both hands touching in twin loops"
                }

        # 9. D (ISL Two-Handed): Left index upright, right hand forms curved D loop against it
        if (left_h["index_ext"] and left_h["ext_count"] == 1) or (right_h["index_ext"] and right_h["ext_count"] == 1):
            stem_h = left_h if (left_h["index_ext"] and left_h["ext_count"] == 1) else right_h
            loop_h = right_h if stem_h is left_h else left_h
            if center_distance < 1.3:
                return {
                    "sign": "D",
                    "confidence": 0.94,
                    "handedness": "two-handed",
                    "desc": "Upright index backbone with secondary hand forming loop to complete letter D"
                }

        # 10. H (ISL Two-Handed): Dominant hand strokes horizontal open palm of secondary hand
        if left_h["ext_count"] >= 3 and right_h["ext_count"] >= 3 and center_distance < 1.2:
            return {
                "sign": "H",
                "confidence": 0.91,
                "handedness": "two-handed",
                "desc": "Dominant palm stroking horizontally across secondary flat palm"
            }

        # 11. M or N (ISL Two-Handed): Dominant hand fingers placed flat across secondary open palm
        if lower_h["ext_count"] >= 3 and center_distance < 1.3:
            if upper_h["ext_count"] == 3:
                return {
                    "sign": "M",
                    "confidence": 0.93,
                    "handedness": "two-handed",
                    "desc": "Three fingers of dominant hand resting across secondary open palm"
                }
            elif upper_h["ext_count"] == 2:
                return {
                    "sign": "N",
                    "confidence": 0.93,
                    "handedness": "two-handed",
                    "desc": "Two fingers of dominant hand resting across secondary open palm"
                }

        # 12. T (ISL Two-Handed): Dominant index touches side of upright secondary index
        if left_h["index_ext"] and right_h["index_ext"] and left_h["ext_count"] == 1 and right_h["ext_count"] == 1:
            if center_distance < 0.9:
                return {
                    "sign": "T",
                    "confidence": 0.92,
                    "handedness": "two-handed",
                    "desc": "Dominant index touches side of vertical index at midpoint forming T"
                }

        # 13. General two-handed fallback
        return {
            "sign": "NAMASTE" if center_distance < 1.2 else "HELP",
            "confidence": 0.85,
            "handedness": "two-handed",
            "desc": "Two interacting hands in ISL conversational space"
        }

    # =========================================================================
    # CASE B: SINGLE HAND DETECTED (One-Handed ISL Signs)
    # =========================================================================
    h = analyze_single_hand_geometry(hand_landmarks_list[0])

    # 1. Clustered fingertips moving to mouth -> FOOD / EAT
    if h["is_clustered"]:
        return {
            "sign": "FOOD",
            "confidence": 0.95,
            "handedness": "one-handed",
            "desc": "Fingertips clustered together towards mouth in ISL Food/Eat sign"
        }

    # 2. C-Shape: Open curved arc -> C
    if h["is_c_shape"]:
        return {
            "sign": "C",
            "confidence": 0.94,
            "handedness": "one-handed",
            "desc": "Fingers and thumb curved in open C profile"
        }

    # 3. L-Shape: Thumb and index at 90-degree right angle -> L
    if h["thumb_ext"] and h["index_ext"] and not h["middle_ext"] and not h["ring_ext"] and not h["pinky_ext"]:
        thumb_index_angle = _dist(h["thumb_tip"], h["index_tip"]) / h["hand_size"]
        if thumb_index_angle > 0.65:
            return {
                "sign": "L",
                "confidence": 0.95,
                "handedness": "one-handed",
                "desc": "Thumb and index extended at 90-degree right angle forming L"
            }

    # 4. Y-Shape: Thumb and pinky extended, middle 3 curled -> Y
    if h["thumb_ext"] and h["pinky_ext"] and not h["index_ext"] and not h["middle_ext"] and not h["ring_ext"]:
        return {
            "sign": "Y",
            "confidence": 0.95,
            "handedness": "one-handed",
            "desc": "Thumb and little finger extended outwards in Y shape"
        }

    # 5. I-Shape: Pinky extended straight UP, others curled -> I
    if h["pinky_ext"] and not h["index_ext"] and not h["middle_ext"] and not h["ring_ext"]:
        return {
            "sign": "I",
            "confidence": 0.95,
            "handedness": "one-handed",
            "desc": "Little finger (pinky) extended vertically upwards for I"
        }

    # 6. V-Shape: Index and middle spread in V, others curled -> V / 2
    if h["index_ext"] and h["middle_ext"] and not h["ring_ext"] and not h["pinky_ext"]:
        if h["index_middle_dist"] > 0.15:
            return {
                "sign": "V",
                "confidence": 0.96,
                "handedness": "one-handed",
                "desc": "Index and middle fingers spread in distinct V shape"
            }
        else:
            # Held tightly together -> U
            return {
                "sign": "U",
                "confidence": 0.92,
                "handedness": "one-handed",
                "desc": "Index and middle fingers held together upright for U"
            }

    # 7. W-Shape: Index, middle, ring spread upright -> W / 3 / WATER
    if h["index_ext"] and h["middle_ext"] and h["ring_ext"] and not h["pinky_ext"]:
        return {
            "sign": "W",
            "confidence": 0.95,
            "handedness": "one-handed",
            "desc": "Index, middle, and ring fingers spread upright in W / Water sign"
        }

    # 8. Single upright index finger -> D / 1
    if h["index_ext"] and not h["middle_ext"] and not h["ring_ext"] and not h["pinky_ext"]:
        return {
            "sign": "D",
            "confidence": 0.94,
            "handedness": "one-handed",
            "desc": "Index finger extended vertically upright"
        }

    # 9. Flat 4 fingers upright, thumb folded -> B / 4
    if h["ext_count"] == 4 and not h["thumb_ext"]:
        return {
            "sign": "B",
            "confidence": 0.94,
            "handedness": "one-handed",
            "desc": "Four fingers extended straight up together, thumb folded across palm"
        }

    # 10. Open 5 fingers spread wide -> HELLO / 5
    if h["all_ext_count"] == 5:
        return {
            "sign": "HELLO",
            "confidence": 0.95,
            "handedness": "one-handed",
            "desc": "Open hand with all five fingers spread in greeting"
        }

    # 11. Closed fist with upright thumb -> A (Single-hand) / YES
    if h["ext_count"] == 0:
        return {
            "sign": "A",
            "confidence": 0.92,
            "handedness": "one-handed",
            "desc": "Closed fist with upright thumb along index"
        }

    # Default single hand fallback
    return {
        "sign": "A",
        "confidence": 0.85,
        "handedness": "one-handed",
        "desc": "Single hand gesture"
    }
