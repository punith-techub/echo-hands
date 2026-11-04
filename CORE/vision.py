"""
ECHOHANDS - Dual-Brain Vision Engine
Hybrid Intelligence Combining:
1. Brain 1: Fine-tuned Residual CNN for 35 Alphanumerics (1-9, A-Z)
2. Brain 2: Deep Feature Vector Prototype Matcher for 50+ ISL Words
With Confidence Calibration, Decision Margins, and Explainable Grad-CAM Heatmaps.
"""

import os
import io
import base64
from typing import Dict, List, Tuple, Optional, Any, Union
import numpy as np
import cv2
import torch
import torch.nn.functional as F
from PIL import Image

from CORE.model_arch import ISLNet
from CORE.isl_trainer import ISLMemoryTrainer
from CORE.sign_knowledge import (
    ALPHANUMERIC_CLASSES,
    CLASS_TO_INDEX,
    INDEX_TO_CLASS,
    get_sign_info,
    is_word,
    is_alphanumeric
)

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
DEFAULT_WEIGHTS_PATH = os.path.join(MODELS_DIR, "alphanumeric_model.pt")

class GradCAM:
    def __init__(self, model: ISLNet, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self._hook_layers()

    def _hook_layers(self):
        def forward_hook(module, input, output):
            self.activations = output

        def backward_hook(module, grad_in, grad_out):
            self.gradients = grad_out[0]

        self.target_layer.register_forward_hook(forward_hook)
        self.target_layer.register_full_backward_hook(backward_hook)

    def generate_heatmap(
        self,
        input_tensor: torch.Tensor,
        target_class_idx: Optional[int] = None,
        prototype_centroid: Optional[torch.Tensor] = None
    ) -> np.ndarray:
        """
        Generate normalized 2D Grad-CAM heatmap array [0.0..1.0] of shape (224, 224).
        Supports:
        1. Brain 1 (Alphanumeric): backprops score = logits[0, target_class_idx]
        2. Brain 2 (Prototype): backprops score = dot(embedding[0], prototype_centroid)
        """
        self.model.zero_grad()
        logits, embedding = self.model(input_tensor)

        if prototype_centroid is not None:
            centroid = prototype_centroid.to(input_tensor.device)
            if centroid.ndim > 1:
                centroid = centroid.view(-1)
            score = torch.dot(embedding[0], centroid)
        else:
            if target_class_idx is None:
                target_class_idx = logits.argmax(dim=1).item()
            score = logits[0, target_class_idx]

        score.backward(retain_graph=True)

        if self.gradients is None or self.activations is None:
            return np.zeros((224, 224), dtype=np.float32)

        # Gradients & Activations: (1, 512, 7, 7)
        grads = self.gradients[0]       # (512, 7, 7)
        acts = self.activations[0]      # (512, 7, 7)

        # Global average pooling of gradients
        weights = torch.mean(grads, dim=(1, 2), keepdim=True)  # (512, 1, 1)

        # Weighted combination of activation maps
        cam = torch.sum(weights * acts, dim=0).detach().cpu().numpy()  # (7, 7)

        # ReLU on activation map
        cam = np.maximum(cam, 0)

        # Normalize to 0..1
        max_val = np.max(cam)
        if max_val > 0:
            cam = cam / max_val
        else:
            cam = np.zeros_like(cam)

        # Resize to input resolution (224, 224) and clip interpolation overshoot
        cam_resized = cv2.resize(cam, (224, 224), interpolation=cv2.INTER_LANCZOS4)
        return np.clip(cam_resized, 0.0, 1.0)

class DualBrainVisionEngine:
    def __init__(
        self,
        weights_path: str = DEFAULT_WEIGHTS_PATH,
        memory_path: Optional[str] = None,
        device: Optional[str] = None
    ):
        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.weights_path = weights_path

        # 1. Initialize Brain 1: Alphanumeric Neural Net
        self.model = ISLNet(num_classes=35, embedding_dim=512).to(self.device)
        self._load_weights()
        self.model.eval()

        # 2. Attach Grad-CAM to Stage 4 Conv Layer
        self.grad_cam = GradCAM(self.model, self.model.stage4)

        # 3. Initialize Brain 2: Continuous Prototype Memory
        self.memory = ISLMemoryTrainer(
            memory_path=memory_path if memory_path else os.path.join(MODELS_DIR, "isl_memory.pt")
        )

        # ImageNet normalization parameters
        self.mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1).to(self.device)
        self.std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1).to(self.device)

    def _load_weights(self):
        if os.path.exists(self.weights_path):
            try:
                state_dict = torch.load(self.weights_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                print(f"[VisionEngine] Loaded trained weights from {self.weights_path}")
            except Exception as e:
                print(f"[VisionEngine] Warning: Could not load weights from {self.weights_path}: {e}")
        else:
            print(f"[VisionEngine] Notice: No weights found at {self.weights_path}. Model using initialized state.")

    def preprocess_tensor(self, rgb_crop: np.ndarray) -> torch.Tensor:
        """Convert (224, 224, 3) RGB numpy array into normalized PyTorch batch tensor."""
        if rgb_crop.shape[:2] != (224, 224):
            rgb_crop = cv2.resize(rgb_crop, (224, 224), interpolation=cv2.INTER_LANCZOS4)

        tensor = torch.from_numpy(rgb_crop).permute(2, 0, 1).unsqueeze(0).float() / 255.0
        tensor = tensor.to(self.device)
        norm_tensor = (tensor - self.mean) / self.std
        return norm_tensor

    def generate_gradcam_overlay(
        self,
        rgb_crop: np.ndarray,
        heatmap_2d: np.ndarray,
        alpha: float = 0.50
    ) -> str:
        """
        Overlay Grad-CAM heatmap with jet/inferno colormap onto original RGB crop.
        Returns base64 data URI string.
        """
        if rgb_crop.shape[:2] != (224, 224):
            rgb_crop = cv2.resize(rgb_crop, (224, 224), interpolation=cv2.INTER_LANCZOS4)

        # Convert heatmap to 0..255 uint8
        heatmap_uint8 = np.uint8(255 * heatmap_2d)
        
        # Apply Jet colormap (OpenCV generates BGR)
        color_heatmap_bgr = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
        color_heatmap_rgb = cv2.cvtColor(color_heatmap_bgr, cv2.COLOR_BGR2RGB)

        # Blend original RGB with heatmap
        blended = np.clip(
            (1.0 - alpha) * rgb_crop.astype(np.float32) + alpha * color_heatmap_rgb.astype(np.float32),
            0, 255
        ).astype(np.uint8)

        # Encode to JPEG base64
        _, buffer = cv2.imencode(".jpg", cv2.cvtColor(blended, cv2.COLOR_RGB2BGR), [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        b64 = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"

    def predict_sign(
        self,
        rgb_crop: np.ndarray,
        is_dual_hand: bool = False,
        preferred_brain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dual-Brain inference on a single 224x224 RGB hand sign crop:
        1. Alphanumeric 35-class classification with logits and margin
        2. Embedding prototype vector matching across 50+ ISL words
        3. Strategic arbitration and Grad-CAM generation
        """
        tensor = self.preprocess_tensor(rgb_crop)
        tensor.requires_grad = True

        # Forward pass
        logits, embedding = self.model(tensor)
        probs = F.softmax(logits, dim=1).detach().cpu().numpy()[0]

        # Top 3 Alphanumeric classes
        top_indices = np.argsort(probs)[::-1][:3]
        top1_idx = int(top_indices[0])
        top1_cls = INDEX_TO_CLASS[top1_idx]
        top1_prob = float(probs[top1_idx])
        top2_prob = float(probs[top_indices[1]]) if len(top_indices) > 1 else 0.0
        decision_margin = top1_prob - top2_prob

        # Brain 2: Prototype Vector Matching
        emb_np = embedding.detach().cpu().numpy()[0]
        word_matches = self.memory.match(emb_np, top_k=5)
        best_sign, best_sign_sim, sign_meta = word_matches[0] if word_matches else ("", 0.0, {})
        is_user_taught = bool(sign_meta.get("is_user_taught", False))

        # Arbitration logic:
        # If user explicitly selected mode, honor it
        if preferred_brain == "word":
            predicted_sign = best_sign
            sign_type = "alphanumeric" if is_alphanumeric(predicted_sign) else "word"
            confidence = float(np.clip(best_sign_sim, 0.0, 1.0))
            chosen_brain = "Brain-2 (Prototype Vector Memory)"
        elif preferred_brain == "alphanumeric":
            predicted_sign = top1_cls
            sign_type = "alphanumeric"
            confidence = top1_prob
            chosen_brain = "Brain-1 (Alphanumeric CNN)"
        else:
            # AUTO MODE:
            # 1. Prioritize user-taught continuous learning prototypes
            if is_user_taught and best_sign_sim >= 0.42:
                predicted_sign = best_sign
                sign_type = "alphanumeric" if is_alphanumeric(predicted_sign) else "word"
                confidence = float(np.clip(best_sign_sim, 0.0, 1.0))
                chosen_brain = "Brain-2 (User-Trained Memory)"
            # 2. Both brains agree on the exact sign
            elif best_sign == top1_cls:
                predicted_sign = top1_cls
                sign_type = "alphanumeric" if is_alphanumeric(predicted_sign) else "word"
                confidence = float(max(top1_prob, best_sign_sim))
                chosen_brain = "Dual-Brain Consensus (CNN + Prototype)"
            # 3. High-confidence prototype match or dual-hand word
            elif (is_dual_hand and best_sign_sim > 0.50) or (best_sign_sim >= 0.70) or (top1_prob < 0.65 and best_sign_sim >= 0.55):
                predicted_sign = best_sign
                sign_type = "alphanumeric" if is_alphanumeric(predicted_sign) else "word"
                confidence = float(np.clip(best_sign_sim, 0.0, 1.0))
                chosen_brain = "Brain-2 (Prototype Vector Memory)"
            # 4. Standard Alphanumeric CNN
            else:
                predicted_sign = top1_cls
                sign_type = "alphanumeric"
                confidence = top1_prob
                chosen_brain = "Brain-1 (Alphanumeric CNN)"

        # Generate Grad-CAM for the top prediction
        try:
            if chosen_brain == "Brain-2 (Prototype Vector Memory)" and predicted_sign in self.memory.prototypes:
                cent = self.memory.prototypes[predicted_sign]["centroid"]
                cam_map = self.grad_cam.generate_heatmap(tensor, prototype_centroid=cent)
            else:
                cam_map = self.grad_cam.generate_heatmap(tensor, target_class_idx=top1_idx)
            gradcam_b64 = self.generate_gradcam_overlay(rgb_crop, cam_map)
        except Exception as e:
            print(f"[VisionEngine] Grad-CAM warning: {e}")
            gradcam_b64 = ""

        # Fetch metadata
        sign_info = get_sign_info(predicted_sign)
        hindi = sign_info.get("hindi", "") if sign_info else ""
        translit = sign_info.get("translit", "") if sign_info else ""
        phonetic = sign_info.get("phonetic", "") if sign_info else ""
        handedness = sign_info.get("handedness", "one-handed") if sign_info else ""

        # Top K candidates
        top_candidates = [
            {"sign": INDEX_TO_CLASS[i], "probability": round(float(probs[i]), 4), "type": "alphanumeric"}
            for i in top_indices
        ]
        for w, sim, m in word_matches:
            top_candidates.append({
                "sign": w,
                "probability": round(float(max(0.0, sim)), 4),
                "type": "word"
            })
        top_candidates = sorted(top_candidates, key=lambda x: x["probability"], reverse=True)[:5]

        return {
            "predicted_sign": predicted_sign,
            "sign_type": sign_type,
            "confidence": round(confidence, 4),
            "decision_margin": round(decision_margin, 4),
            "chosen_brain": chosen_brain,
            "hindi_translation": hindi,
            "hindi_transliteration": translit,
            "phonetic_pronunciation": phonetic,
            "handedness": handedness,
            "is_dual_hand": is_dual_hand,
            "top_candidates": top_candidates,
            "gradcam_heatmap": gradcam_b64
        }
