"""
ECHOHANDS - Multi-Sign Engine
Advanced spatial segmentation, dual-hand spatial envelope merging,
multi-sign strip parsing in reading order (Left-to-Right, Top-to-Bottom),
and optical zoom square cropping.
"""

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
        row_height_tolerance: float = 0.25
    ):
        self.target_size = target_size
        self.padding_ratio = padding_ratio
        self.min_area_fraction = min_area_fraction
        self.max_area_fraction = max_area_fraction
        self.dual_hand_dist_threshold = dual_hand_dist_threshold
        self.row_height_tolerance = row_height_tolerance

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

    def segment_skin(self, image: Union[np.ndarray, Image.Image], is_bgr: bool = False) -> np.ndarray:
        """
        Dual-color-space skin detection using YCrCb and HSV thresholding on RGB representation,
        with morphological noise filtration and fallback saliency.
        """
        bgr, rgb = self._ensure_bgr_rgb(image, is_bgr=is_bgr)
        h, w = rgb.shape[:2]
        total_pixels = h * w

        # 1. YCrCb Color Space directly from RGB
        ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)
        # Skin in YCrCb: Y in [30, 255], Cr in [130, 180], Cb in [77, 130]
        lower_ycrcb = np.array([30, 130, 77], dtype=np.uint8)
        upper_ycrcb = np.array([255, 180, 130], dtype=np.uint8)
        mask_ycrcb = cv2.inRange(ycrcb, lower_ycrcb, upper_ycrcb)

        # 2. HSV Color Space directly from RGB
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        lower_hsv1 = np.array([0, 20, 40], dtype=np.uint8)
        upper_hsv1 = np.array([28, 220, 255], dtype=np.uint8)
        mask_hsv1 = cv2.inRange(hsv, lower_hsv1, upper_hsv1)

        lower_hsv2 = np.array([160, 20, 40], dtype=np.uint8)
        upper_hsv2 = np.array([180, 220, 255], dtype=np.uint8)
        mask_hsv2 = cv2.inRange(hsv, lower_hsv2, upper_hsv2)
        mask_hsv = cv2.bitwise_or(mask_hsv1, mask_hsv2)

        # Combine both representations
        combined_mask = cv2.bitwise_and(mask_ycrcb, mask_hsv)

        # Morphological operations to remove noise and fill voids
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        cleaned_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        # Check if enough skin pixels were detected
        detected_pixels = cv2.countNonZero(cleaned_mask)
        skin_ratio = detected_pixels / total_pixels

        # Fallback if skin ratio is extremely low (e.g. artificial diagrams, sketch/chalkboard gestures, extreme lighting)
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

                    # Only merge if touching or very close relative to hand size
                    # In a multi-sign strip, signs are spaced by at least 25% of hand width
                    max_gap = min_w * 0.20
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
        is_bgr: bool = False
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

        mask = self.segment_skin(rgb, is_bgr=False)

        # Find external contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        raw_boxes = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_area <= area <= max_area:
                bx, by, bw, bh = cv2.boundingRect(cnt)
                # Ignore extreme aspect ratio artifacts (e.g. single thin hair or edge line)
                aspect = bw / float(bh) if bh > 0 else 1.0
                if 0.15 <= aspect <= 6.0:
                    raw_boxes.append((bx, by, bw, bh))

        # If no contours match or image is already an isolated sign, use whole image
        if not raw_boxes:
            # Whole image fallback
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
