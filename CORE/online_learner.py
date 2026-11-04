"""
ECHOHANDS 5.0 - Online Self-Learning Engine
Performs real-time offline gradient descent and prototype adaptation upon user feedback.
When a user clicks Thumbs Down and enters a correction:
1. Executes an online gradient descent step on ISLNet's classifier head with
   margin-based punishment against the false prediction and cross-entropy for the correct sign.
2. Applies experience replay with verified class anchors to prevent catastrophic forgetting.
3. Repels false prototypes and reinforces correct prototypes in ISLMemoryTrainer.
4. Persists updated model weights (models/alphanumeric_model.pt) and memory (models/isl_memory.pt).
"""

import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Dict, Any, List

from CORE.model_arch import ISLNet
from CORE.sign_knowledge import (
    ALPHANUMERIC_CLASSES,
    CLASS_TO_INDEX,
    INDEX_TO_CLASS,
    is_alphanumeric,
    is_word
)

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
MODEL_PATH = os.path.join(MODELS_DIR, "alphanumeric_model.pt")
EXPERIENCE_PATH = os.path.join(MODELS_DIR, "experience_memory.pt")
ANCHORS_PATH = os.path.join(MODELS_DIR, "class_anchors.pt")


class OnlineLearner:
    def __init__(self, model: ISLNet, memory_trainer):
        self.model = model
        self.memory = memory_trainer
        self.experience_buffer: List[Dict[str, Any]] = []
        self._load_experience()
        self.anchors = None
        if os.path.exists(ANCHORS_PATH):
            try:
                self.anchors = torch.load(ANCHORS_PATH, map_location="cpu")
            except Exception as e:
                print(f"[OnlineLearner] Warning: Could not load anchors: {e}")

    def _load_experience(self):
        """Load stored user corrections for experience replay."""
        if os.path.exists(EXPERIENCE_PATH):
            try:
                data = torch.load(EXPERIENCE_PATH, map_location="cpu")
                if isinstance(data, list):
                    self.experience_buffer = data
                    print(f"[OnlineLearner] Loaded {len(self.experience_buffer)} past user experience items.")
            except Exception as e:
                print(f"[OnlineLearner] Warning: Failed to load experience replay buffer: {e}")
                self.experience_buffer = []

    def _save_experience(self):
        """Persist experience replay buffer to disk."""
        try:
            torch.save(self.experience_buffer, EXPERIENCE_PATH)
        except Exception as e:
            print(f"[OnlineLearner] Warning: Failed to save experience replay buffer: {e}")

    def learn_from_feedback(
        self,
        crop_rgb: np.ndarray,
        wrong_sign: str,
        correct_sign: str,
        is_dual_hand: bool = False
    ) -> Dict[str, Any]:
        """
        Severe Negative Reinforcement & Online Gradient Backpropagation:
        - Penalizes wrong_sign to suppress its activations on this gesture.
        - Strongly rewards and trains correct_sign across both CNN and Prototype Memory.
        - Replays past experiences + anchor regularization to maintain global benchmark accuracy.
        """
        norm_wrong = wrong_sign.strip().upper()
        norm_correct = correct_sign.strip().upper()

        # 1. Preprocess crop into tensor and extract current features
        crop_float = crop_rgb.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        inp = (crop_float - mean) / std
        tensor = torch.from_numpy(inp).permute(2, 0, 1).unsqueeze(0).float()

        # Keep model in eval mode so BatchNorm running stats are untouched
        self.model.eval()
        with torch.no_grad():
            activations = self.model.features(tensor)
            pooled = self.model.pool(activations).flatten(1)
            raw_emb = self.model.neck(pooled)
            norm_emb = F.normalize(raw_emb, p=2, dim=1)
            feature_np = norm_emb.cpu().numpy()[0]

        # 2. Add to experience buffer
        exp_item = {
            "correct_sign": norm_correct,
            "wrong_sign": norm_wrong,
            "norm_embedding": norm_emb.cpu().clone(),
            "is_dual_hand": is_dual_hand
        }
        self.experience_buffer.append(exp_item)
        if len(self.experience_buffer) > 200:
            self.experience_buffer.pop(0)
        self._save_experience()

        # 3. Online Neural Network Backpropagation (if correct_sign is an alphanumeric class)
        cnn_updated = False
        if is_alphanumeric(norm_correct):
            correct_idx = CLASS_TO_INDEX[norm_correct]
            wrong_idx = CLASS_TO_INDEX.get(norm_wrong, None)

            # Build replay batch:
            replay_feats = [norm_emb.clone()]
            replay_labels = [correct_idx]
            replay_wrongs = [wrong_idx]

            for past in self.experience_buffer[-20:]:
                past_correct = past["correct_sign"]
                if is_alphanumeric(past_correct):
                    replay_feats.append(past["norm_embedding"].clone())
                    replay_labels.append(CLASS_TO_INDEX[past_correct])
                    past_w = past.get("wrong_sign")
                    replay_wrongs.append(CLASS_TO_INDEX.get(past_w, None) if past_w else None)

            # Train classifier head strictly (Linear layer without batchnorm side effects)
            self.model.eval()
            optimizer = torch.optim.AdamW(
                self.model.classifier.parameters(),
                lr=0.008,
                weight_decay=1e-4
            )

            anchor_labels = torch.arange(len(ALPHANUMERIC_CLASSES))

            for step in range(25):
                optimizer.zero_grad()
                total_loss = 0.0

                # Train on user experiences with feature jitter
                for feat, lbl, wrg in zip(replay_feats, replay_labels, replay_wrongs):
                    noise = torch.randn_like(feat) * 0.015
                    jittered = (feat + noise) * 20.0
                    logits = self.model.classifier(jittered)

                    ce_loss = F.cross_entropy(logits, torch.tensor([lbl]))
                    punish_loss = 0.0
                    if wrg is not None and wrg != lbl:
                        margin_diff = logits[0, wrg] - logits[0, lbl] + 3.0
                        punish_loss = 3.0 * torch.relu(margin_diff)

                    total_loss += ce_loss + punish_loss

                # Regularize with clean class anchors to prevent drift
                if self.anchors is not None:
                    anchor_logits = self.model.classifier(self.anchors * 20.0)
                    loss_anchors = 0.8 * F.cross_entropy(anchor_logits, anchor_labels)
                    total_loss += loss_anchors

                total_loss.backward()
                optimizer.step()

            self.model.eval()
            cnn_updated = True

            # Save updated weights
            try:
                torch.save(self.model.state_dict(), MODEL_PATH)
                print(f"[OnlineLearner] Successfully trained & saved alphanumeric model weights for '{norm_correct}'.")
            except Exception as e:
                print(f"[OnlineLearner] Warning: Failed to save model weights: {e}")

        # 4. Prototype Memory Reinforcement & Severe Punishment
        mem_result = self.memory.punish_and_correct(
            wrong_word=norm_wrong,
            correct_word=norm_correct,
            feature_vector=feature_np,
            punishment_factor=0.75
        )

        # Mark correct sign in prototype memory as explicitly user-taught
        if norm_correct in self.memory.prototypes:
            self.memory.prototypes[norm_correct].setdefault("metadata", {})
            self.memory.prototypes[norm_correct]["metadata"]["is_user_taught"] = True
            self.memory.save()

        return {
            "status": "success",
            "cnn_weights_trained": cnn_updated,
            "prototype_memory_updated": True,
            "correct_sign": norm_correct,
            "wrong_sign": norm_wrong,
            "experience_buffer_size": len(self.experience_buffer),
            "memory_details": mem_result
        }

    def reward_prediction(self, sign: str, crop_rgb: np.ndarray) -> Dict[str, Any]:
        """Reward model for a confirmed prediction."""
        norm_sign = sign.strip().upper()
        crop_float = crop_rgb.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        inp = (crop_float - mean) / std
        tensor = torch.from_numpy(inp).permute(2, 0, 1).unsqueeze(0).float()

        self.model.eval()
        with torch.no_grad():
            activations = self.model.features(tensor)
            pooled = self.model.pool(activations).flatten(1)
            raw_emb = self.model.neck(pooled)
            norm_emb = F.normalize(raw_emb, p=2, dim=1)
            feature_np = norm_emb.cpu().numpy()[0]

        res = self.memory.reward_prediction(norm_sign, feature_np)
        return {
            "status": "success",
            "sign": norm_sign,
            "details": res
        }
