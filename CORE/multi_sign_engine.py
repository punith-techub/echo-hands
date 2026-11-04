"""
ECHOHANDS - Multi-Sign Engine
Advanced spatial segmentation, dual-hand spatial envelope merging,
multi-sign strip parsing in reading order (Left-to-Right, Top-to-Bottom),
and optical zoom square cropping.
"""

import os
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional, Union
from PIL import Image

@dataclass
class SignRegion:
    index: int
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    crop: np.ndarray                 # 224x224 RGB image
    is_dual_hand: bool
    aspect_ratio: float
    area: int
    confidence_scale: float = 1.0

class MultiSignEngine:
    def __init__(
        self,
        target_size: Tuple[int, int] = (224, 224),
        padding_ratio: float = 0.18,
        min_area_fraction: float = 0.002,
        max_area_fraction: float = 0.98,
        dual_hand_dist_threshold: float = 0.35,
        row_height_tolerance: float = 0.08
    ):
        self.target_size = target_size
        self.padding_ratio = padding_ratio
        self.min_area_fraction = min_area_fraction
        self.max_area_fraction = max_area_fraction
        self.dual_hand_dist_threshold = dual_hand_dist_threshold
        self.row_height_tolerance = row_height_tolerance

        # Initialize YuNet Deep Neural Face Detector (Ultra-fast <6ms inference)
        self.face_detector = None
        face_model_path = os.path.join(os.path.dirname(__file__), "..", "models", "face_detection_yunet_2023mar.onnx")
        if os.path.exists(face_model_path) and hasattr(cv2, "FaceDetectorYN"):
            try:
                self.face_detector = cv2.FaceDetectorYN.create(face_model_path, "", (320, 240), score_threshold=0.55)
            except Exception as e:
                print(f"[MultiSignEngine] Face detector warning: {e}")

    def detect_and_mask_faces(self, rgb: np.ndarray, skin_mask: np.ndarray) -> np.ndarray:
        """
        Detect human faces and mask them out so the user's face, neck, and forehead
        are NEVER misclassified as a hand sign (preventing face predicting as '3').
        """
        if self.face_detector is None:
            return skin_mask

        h, w = rgb.shape[:2]
        small_w, small_h = 320, 240
        small = cv2.resize(rgb, (small_w, small_h))
        self.face_detector.setInputSize((small_w, small_h))
        _, faces = self.face_detector.detect(small)

        if faces is not None:
            scale_x = w / float(small_w)
            scale_y = h / float(small_h)
            for face in faces:
                fx = int(face[0] * scale_x)
                fy = int(face[1] * scale_y)
                fw = int(face[2] * scale_x)
                fh = int(face[3] * scale_y)
                # Keep face mask tight to the head so it does NOT cut off hands signing at chest/chin level!
                pad_x = int(fw * 0.08)
                pad_top = int(fh * 0.12)
                pad_bot = int(fh * 0.05)  # Stops at chin, leaves chest/hands 100% intact!
                x1 = max(0, fx - pad_x)
                y1 = max(0, fy - pad_top)
                x2 = min(w, fx + fw + pad_x)
                y2 = min(h, fy + fh + pad_bot)
                skin_mask[y1:y2, x1:x2] = 0

        return skin_mask

    def _ensure_bgr_rgb(self, image: Union[np.ndarray, Image.Image], is_bgr: bool = False) -> Tuple[np.ndarray, np.ndarray]:
        """Convert input image into both BGR (for OpenCV) and RGB formats."""
        if isinstance(image, Image.Image):
            rgb = np.array(image.convert("RGB"))
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            return bgr, rgb
        elif isinstance(image, np.ndarray):
            if len(image.shape) == 2:
                # Grayscale to 3-channel
                bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:
                # RGBA to RGB & BGR
                rgb = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
                bgr = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
            elif is_bgr:
                bgr = image
                rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                # Default for numpy arrays from PIL/web is RGB
                rgb = image
                bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            return bgr, rgb
        else:
            raise TypeError(f"Unsupported image type: {type(image)}")

    def segment_skin(
        self,
        image: Union[np.ndarray, Image.Image],
        is_bgr: bool = False,
        allow_empty: bool = False,
        mask_faces: bool = True
    ) -> np.ndarray:
        """
        Dual-color-space skin detection using YCrCb and HSV thresholding on RGB representation,
        with morphological noise filtration and fallback saliency.
        """
        bgr, rgb = self._ensure_bgr_rgb(image, is_bgr=is_bgr)
        h, w = rgb.shape[:2]
        total_pixels = h * w

        # 1. YCrCb Color Space directly from RGB (covers diverse Indian skin tones: fair to dark brown)
        ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)
        lower_ycrcb = np.array([30, 130, 75], dtype=np.uint8)
        upper_ycrcb = np.array([255, 185, 135], dtype=np.uint8)
        mask_ycrcb = cv2.inRange(ycrcb, lower_ycrcb, upper_ycrcb)

        # 2. HSV Color Space directly from RGB
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        lower_hsv1 = np.array([0, 20, 30], dtype=np.uint8)
        upper_hsv1 = np.array([26, 235, 255], dtype=np.uint8)
        mask_hsv1 = cv2.inRange(hsv, lower_hsv1, upper_hsv1)

        lower_hsv2 = np.array([160, 20, 30], dtype=np.uint8)
        upper_hsv2 = np.array([180, 235, 255], dtype=np.uint8)
        mask_hsv2 = cv2.inRange(hsv, lower_hsv2, upper_hsv2)
        mask_hsv = cv2.bitwise_or(mask_hsv1, mask_hsv2)

        # Combine both representations
        combined_mask = cv2.bitwise_and(mask_ycrcb, mask_hsv)

        # Morphological operations to remove noise and fill voids
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        cleaned_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        # If combined mask lost hand pixels due to indoor/YouTube lighting, fall back to YCrCb alone
        if cv2.countNonZero(cleaned_mask) < (total_pixels * 0.003):
            cleaned_mask = cv2.morphologyEx(mask_ycrcb, cv2.MORPH_OPEN, kernel, iterations=1)
            cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        # In webcam mode: MASK OUT FACES
        if mask_faces and self.face_detector is not None:
            cleaned_mask = self.detect_and_mask_faces(rgb, cleaned_mask)

        # Check if enough skin pixels were detected
        detected_pixels = cv2.countNonZero(cleaned_mask)
        skin_ratio = detected_pixels / total_pixels

        # If webcam mode: If skin ratio is low, return empty mask cleanly
        if allow_empty:
            if skin_ratio < 0.002:
                return np.zeros((h, w), dtype=np.uint8)
            return cleaned_mask

        # Fallback ONLY for static benchmark diagrams/chips with extreme white balance
        if skin_ratio < 0.005:
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            mean_border = (np.mean(gray[0, :]) + np.mean(gray[-1, :]) + np.mean(gray[:, 0]) + np.mean(gray[:, -1])) / 4.0
            if mean_border > 128:
                _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            else:
                _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            dilated = cv2.dilate(otsu, kernel, iterations=2)
            return dilated

        return cleaned_mask

    def _merge_dual_hands(
        self,
        boxes: List[Tuple[int, int, int, int]],
        img_w: int,
        img_h: int
    ) -> List[Tuple[int, int, int, int, bool]]:
        """
        Merge adjacent or interacting hands into a unified dual-hand envelope.
        Returns list of (x, y, w, h, is_dual_hand).
        CRITICAL: Only merges hands that are part of the SAME two-handed sign.
        Never merges distinct signs spaced out in a multi-sign strip.
        """
        if not boxes:
            return []

        # Convert to [x1, y1, x2, y2, is_dual]
        items = []
        for (x, y, w, h) in boxes:
            items.append([x, y, x + w, y + h, False])

        changed = True
        while changed:
            changed = False
            new_items = []
            skip = set()

            for i in range(len(items)):
                if i in skip:
                    continue
                x1_a, y1_a, x2_a, y2_a, dual_a = items[i]
                w_a = x2_a - x1_a
                h_a = y2_a - y1_a

                merged = False
                for j in range(i + 1, len(items)):
                    if j in skip:
                        continue
                    x1_b, y1_b, x2_b, y2_b, dual_b = items[j]
                    w_b = x2_b - x1_b
                    h_b = y2_b - y1_b

                    # Check spatial overlap or extreme proximity for interacting hands
                    # 1. Horizontal gap (0 if overlapping)
                    h_gap = max(0, max(x1_a, x1_b) - min(x2_a, x2_b))
                    # 2. Vertical overlap extent
                    v_overlap_len = max(0, min(y2_a, y2_b) - max(y1_a, y1_b))
                    min_h = min(h_a, h_b)
                    min_w = min(w_a, w_b)

                    # Dual-hand merging rules:
                    # When 3 or more hands are present, it is a multi-sign strip or sentence poster.
                    # In a strip/sequence, distinct side-by-side hands must only merge if overlapping (h_gap == 0).
                    # For an isolated 2-hand scene, interacting hands in close proximity merge into a dual-hand envelope.
                    is_multi_sequence = len(boxes) >= 3
                    max_gap = 0 if is_multi_sequence else max(12, int(min_w * 0.25))
                    is_vert_aligned = v_overlap_len > (min_h * 0.35)

                    merged_w = max(x2_a, x2_b) - min(x1_a, x1_b)
                    merged_h = max(y2_a, y2_b) - min(y1_a, y1_b)
                    merged_aspect = merged_w / float(merged_h) if merged_h > 0 else 1.0

                    # Dual-hand envelopes are compact (aspect ratio <= 2.0)
                    if (h_gap <= max_gap and is_vert_aligned and merged_aspect <= 2.0):
                        x1_merged = min(x1_a, x1_b)
                        y1_merged = min(y1_a, y1_b)
                        x2_merged = max(x2_a, x2_b)
                        y2_merged = max(y2_a, y2_b)
                        new_items.append([x1_merged, y1_merged, x2_merged, y2_merged, True])
                        skip.add(j)
                        merged = True
                        changed = True
                        break

                if not merged:
                    new_items.append([x1_a, y1_a, x2_a, y2_a, dual_a])

            items = new_items

        result = []
        for x1, y1, x2, y2, dual in items:
            result.append((int(x1), int(y1), int(x2 - x1), int(y2 - y1), dual))
        return result

    def _sort_reading_order(
        self,
        boxes_with_flags: List[Tuple[int, int, int, int, bool]],
        img_h: int
    ) -> List[Tuple[int, int, int, int, bool]]:
        """
        Sort bounding boxes in natural reading order: Top-to-Bottom, Left-to-Right.
        Clusters boxes into lines/rows based on Y overlap.
        """
        if len(boxes_with_flags) <= 1:
            return boxes_with_flags

        # Sort primarily by y
        sorted_by_y = sorted(boxes_with_flags, key=lambda b: b[1])

        # Cluster into rows
        rows: List[List[Tuple[int, int, int, int, bool]]] = []
        y_thresh = img_h * self.row_height_tolerance

        current_row = [sorted_by_y[0]]
        current_y_center = sorted_by_y[0][1] + sorted_by_y[0][3] / 2.0

        for box in sorted_by_y[1:]:
            box_y_center = box[1] + box[3] / 2.0
            if abs(box_y_center - current_y_center) < y_thresh:
                current_row.append(box)
                # Update rolling center
                current_y_center = sum(b[1] + b[3] / 2.0 for b in current_row) / len(current_row)
            else:
                rows.append(current_row)
                current_row = [box]
                current_y_center = box_y_center
        if current_row:
            rows.append(current_row)

        # Sort each row horizontally (Left-to-Right)
        final_ordered = []
        for row in rows:
            sorted_row = sorted(row, key=lambda b: b[0])
            final_ordered.extend(sorted_row)

        return final_ordered

    def _crop_square_normalized(
        self,
        rgb_image: np.ndarray,
        bbox: Tuple[int, int, int, int]
    ) -> np.ndarray:
        """
        Extract optical zoom crop with padding and square aspect ratio normalization.
        """
        h_img, w_img = rgb_image.shape[:2]
        x, y, w, h = bbox

        # Add padding
        pad_x = int(w * self.padding_ratio)
        pad_y = int(h * self.padding_ratio)

        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(w_img, x + w + pad_x)
        y2 = min(h_img, y + h + pad_y)

        crop_w = x2 - x1
        crop_h = y2 - y1

        # Make crop square without distortion by padding symmetrically
        max_side = max(crop_w, crop_h)
        diff_w = max_side - crop_w
        diff_h = max_side - crop_h

        pad_left = diff_w // 2
        pad_right = diff_w - pad_left
        pad_top = diff_h // 2
        pad_bottom = diff_h - pad_top

        # Sub-crop from original
        sub = rgb_image[y1:y2, x1:x2]

        # Pad with neutral background color (mean of borders or zero)
        if sub.size == 0:
            # Fallback blank
            return np.zeros((self.target_size[1], self.target_size[0], 3), dtype=np.uint8)

        bordered = cv2.copyMakeBorder(
            sub,
            pad_top, pad_bottom, pad_left, pad_right,
            cv2.BORDER_CONSTANT,
            value=[15, 18, 24]  # Tactical dark slate backdrop
        )

        # Resize to target size (224, 224)
        resized = cv2.resize(bordered, self.target_size, interpolation=cv2.INTER_LANCZOS4)
        return resized

    def extract_signs(
        self,
        image: Union[np.ndarray, Image.Image],
        is_bgr: bool = False,
        allow_empty: bool = False
    ) -> List[SignRegion]:
        """
        High-level pipeline:
        1. Color segmentation & contour discovery
        2. Filter noise and envelope merging
        3. Reading order sorting (Left-to-Right, Top-to-Bottom)
        4. Optical zoom square cropping
        """
        bgr, rgb = self._ensure_bgr_rgb(image, is_bgr=is_bgr)
        h, w = rgb.shape[:2]
        total_area = h * w
        min_area = total_area * self.min_area_fraction
        max_area = total_area * self.max_area_fraction

        mask = self.segment_skin(rgb, is_bgr=False, allow_empty=allow_empty, mask_faces=allow_empty)

        # Find external contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        raw_boxes = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Area gating (allows hands from medium-shot YouTube videos and close-up webcams)
            c_min_area = total_area * (0.0015 if allow_empty else self.min_area_fraction)
            c_max_area = total_area * (0.50 if allow_empty else self.max_area_fraction)
            if c_min_area <= area <= c_max_area:
                bx, by, bw, bh = cv2.boundingRect(cnt)

                # REJECT BACKGROUND DOORS & FURNITURE IN WEBCAM STREAM:
                if allow_empty:
                    # 1. Door touches top of frame and spans more than 60% of vertical height
                    if by <= 2 and bh > (h * 0.60):
                        continue
                    # 2. Touches both horizontal borders
                    if bx <= 2 and (bx + bw) >= (w - 3):
                        continue
                    # 3. High solidity (>0.94) rectangle with huge area: flat door panels or cabinets
                    box_area = bw * bh
                    solidity = area / float(box_area) if box_area > 0 else 0
                    if solidity > 0.94 and area > (total_area * 0.15):
                        continue
                    # 4. Aspect ratio check for hands: ISL hand bounding boxes are 0.20 to 4.5
                    aspect = bw / float(bh) if bh > 0 else 1.0
                    if not (0.20 <= aspect <= 4.5):
                        continue
                else:
                    aspect = bw / float(bh) if bh > 0 else 1.0
                    if not (0.15 <= aspect <= 6.0):
                        continue

                raw_boxes.append((bx, by, bw, bh))

        # If no contours match and allow_empty is requested (e.g. live webcam stream), return empty
        if not raw_boxes:
            if allow_empty:
                return []
            # Whole image fallback for pre-cropped static benchmark samples
            crop = self._crop_square_normalized(rgb, (0, 0, w, h))
            return [
                SignRegion(
                    index=0,
                    bbox=(0, 0, w, h),
                    crop=crop,
                    is_dual_hand=False,
                    aspect_ratio=w / float(h),
                    area=total_area,
                    confidence_scale=1.0
                )
            ]

        # Merge dual hands if nearby
        merged_boxes = self._merge_dual_hands(raw_boxes, w, h)

        # Sort in reading order
        ordered_boxes = self._sort_reading_order(merged_boxes, h)

        sign_regions = []
        for idx, (bx, by, bw, bh, is_dual) in enumerate(ordered_boxes):
            crop = self._crop_square_normalized(rgb, (bx, by, bw, bh))
            sign_regions.append(
                SignRegion(
                    index=idx,
                    bbox=(bx, by, bw, bh),
                    crop=crop,
                    is_dual_hand=is_dual,
                    aspect_ratio=bw / float(bh) if bh > 0 else 1.0,
                    area=bw * bh,
                    confidence_scale=1.0
                )
            )

        return sign_regions
