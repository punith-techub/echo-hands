"""
ECHOHANDS - ISL Continuous Learning Prototype Memory
Local offline continuous learning prototype vector memory manager.
Stores and matches deep feature embeddings for 50+ ISL word gestures
using Cosine Similarity with zero-shot prototype registration.
"""

import os
import math
import cv2
from typing import Dict, List, Tuple, Optional, Any, Union
import torch
import torch.nn.functional as F
import numpy as np

from CORE.sign_knowledge import ISL_WORDS_METADATA, get_sign_info

DEFAULT_MEMORY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "isl_memory.pt")

def render_word_glyph(word_name: str, size: int = 224, seed: int = 42) -> np.ndarray:
    """
    Render distinctive visual gesture crop for ISL words in 224x224 RGB.
    """
    np.random.seed(seed)
    skin = (175, 120, 85)  # Wheatish brown in BGR
    img = np.ones((size, size, 3), dtype=np.uint8) * 32
    cx, cy = size // 2, size // 2 + 15

    w = word_name.upper()
    if w == "NAMASTE":
        # Two flat palms pressed together upright at chest level
        cv2.ellipse(img, (cx - 14, cy), (18, 55), -10, 0, 360, skin, -1)
        cv2.ellipse(img, (cx + 14, cy), (18, 55), 10, 0, 360, skin, -1)
        cv2.line(img, (cx - 6, cy - 50), (cx + 6, cy - 50), (int(skin[0]*0.95), int(skin[1]*0.95), int(skin[2]*0.95)), 14)
        cv2.rectangle(img, (cx - 28, cy + 40), (cx + 28, size - 2), (int(skin[0]*0.85), int(skin[1]*0.85), int(skin[2]*0.85)), -1)
    elif w == "HELP":
        # Closed fist on flat horizontal palm
        cv2.ellipse(img, (cx, cy + 35), (60, 20), 0, 0, 360, skin, -1)
        cv2.circle(img, (cx, cy - 15), 34, (int(skin[0]*0.92), int(skin[1]*0.92), int(skin[2]*0.92)), -1)
        cv2.line(img, (cx - 12, cy - 20), (cx - 12, cy - 58), skin, 14)
        cv2.rectangle(img, (cx - 18, cy + 50), (cx + 18, size - 2), (int(skin[0]*0.8), int(skin[1]*0.8), int(skin[2]*0.8)), -1)
    elif w in ("FOOD", "EAT"):
        # Flattened O hand touching mouth
        cv2.circle(img, (cx, cy - 20), 30, skin, -1)
        cv2.ellipse(img, (cx, cy - 45), (15, 20), 0, 0, 360, skin, -1)
    elif w in ("WATER", "DRINK"):
        # W handshape touching chin
        cv2.circle(img, (cx, cy + 10), 32, skin, -1)
        for i in [-15, 0, 15]:
            cv2.line(img, (cx + i, cy + 5), (int(cx + i * 1.3), cy - 50), skin, 12)
    elif w == "STOP":
        # Vertical chop onto horizontal palm
        cv2.ellipse(img, (cx, cy + 25), (55, 18), 0, 0, 360, skin, -1)
        cv2.rectangle(img, (cx - 12, cy - 50), (cx + 12, cy + 25), skin, -1)
    elif w == "PLEASE":
        # Open flat palm rubbing chest
        cv2.circle(img, (cx, cy), 42, skin, -1)
        cv2.circle(img, (cx, cy), 15, (int(skin[0]*1.1 % 255), int(skin[1]*0.8), int(skin[2]*0.8)), 4)
    elif w == "SORRY":
        # Closed fist rubbing chest
        cv2.circle(img, (cx, cy), 35, skin, -1)
        cv2.line(img, (cx - 10, cy - 10), (cx - 10, cy - 42), skin, 12)
    elif w == "THANK_YOU":
        # Hand moving out from chin
        cv2.ellipse(img, (cx, cy - 25), (25, 45), 25, 0, 360, skin, -1)
    elif w == "CAT":
        # Whiskers spreading from cheek
        cv2.circle(img, (cx - 30, cy), 28, skin, -1)
        cv2.line(img, (cx - 20, cy - 15), (cx + 50, cy - 30), skin, 8)
        cv2.line(img, (cx - 20, cy), (cx + 55, cy), skin, 8)
        cv2.line(img, (cx - 20, cy + 15), (cx + 50, cy + 30), skin, 8)
    else:
        # Structured semantic gesture uniquely parameterized by word hash
        h = sum(ord(c) * (i * 37 + 13) for i, c in enumerate(w))
        radius = 28 + (h % 14)
        cv2.circle(img, (cx, cy), radius, skin, -1)
        num_prongs = (h % 5) + 1
        base_angle = -60 + (h % 25)
        sweep = 90 + ((h // 5) % 40)
        length = 45 + ((h // 13) % 25)
        for p in range(num_prongs):
            angle = base_angle + p * (sweep / max(1, num_prongs - 1))
            rad = math.radians(angle - 90)
            fx = int(cx + length * math.cos(rad))
            fy = int(cy + length * math.sin(rad))
            cv2.line(img, (cx, cy), (fx, fy), skin, 13)
            cv2.circle(img, (fx, fy), 7, (int(skin[0]*0.9), int(skin[1]*0.9), int(skin[2]*0.9)), -1)
        if (h % 2) == 0:
            cv2.ellipse(img, (cx, cy + 20), (radius + 10, 16), 0, 0, 360, (int(skin[0]*0.85), int(skin[1]*0.85), int(skin[2]*0.85)), -1)

    img = cv2.GaussianBlur(img, (3, 3), 0)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

class ISLMemoryTrainer:
    def __init__(self, memory_path: str = DEFAULT_MEMORY_PATH, feature_dim: int = 512, model=None):
        self.memory_path = memory_path
        self.feature_dim = feature_dim
        self.model = model
        # Dictionary: word -> {"centroid": torch.Tensor (D,), "samples": int, "metadata": dict}
        self.prototypes: Dict[str, Dict[str, Any]] = {}
        self.load_or_initialize()

    def load_or_initialize(self) -> None:
        """Load memory file if it exists, or initialize with pre-seeded anchors."""
        if os.path.exists(self.memory_path):
            try:
                checkpoint = torch.load(self.memory_path, map_location="cpu")
                if "prototypes" in checkpoint:
                    self.prototypes = checkpoint["prototypes"]
                    self.feature_dim = checkpoint.get("feature_dim", self.feature_dim)
                    return
            except Exception as e:
                print(f"[ISLMemoryTrainer] Warning: Error loading {self.memory_path}: {e}. Reinitializing.")

        # Initialize pre-seeded prototypes for all known ISL words
        self._initialize_default_prototypes()
        self.save()

    def populate_initial_words(self, model=None) -> None:
        """Alias for _initialize_default_prototypes with optional model override."""
        self._initialize_default_prototypes(model=model)

    def _initialize_default_prototypes(self, model=None) -> None:
        """
        Synthesize distinctive visual prototype anchors for 60+ ISL words
        grounded in the neural feature embedding space.
        """
        from CORE.model_arch import ISLNet
        from CORE.multi_sign_engine import MultiSignEngine
        sign_engine = MultiSignEngine(min_area_fraction=0.002)

        active_model = model or self.model
        if active_model is None:
            active_model = ISLNet()
            weights_path = os.path.join(os.path.dirname(os.path.abspath(self.memory_path)), "alphanumeric_model.pt")
            if os.path.exists(weights_path):
                try:
                    active_model.load_state_dict(torch.load(weights_path, map_location="cpu"))
                except Exception:
                    pass
        active_model.eval()

        mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)

        for word, meta in ISL_WORDS_METADATA.items():
            if word in self.prototypes and self.prototypes[word].get("metadata", {}).get("is_user_taught"):
                continue
            glyph = render_word_glyph(word, size=224, seed=sum(ord(c) for c in word))
            regions = sign_engine.extract_signs(glyph)
            crop = regions[0].crop if regions else glyph
            tensor = torch.from_numpy(crop).permute(2, 0, 1).unsqueeze(0).float() / 255.0
            norm_tensor = (tensor - mean) / std
            with torch.no_grad():
                _, emb = active_model.extract_features(norm_tensor)
                emb_norm = F.normalize(emb[0], p=2, dim=0)

            self.prototypes[word] = {
                "centroid": emb_norm.cpu(),
                "samples": 3,
                "metadata": {
                    "category": meta.get("category", "action"),
                    "hindi": meta.get("hindi", ""),
                    "handedness": meta.get("handedness", "one-handed")
                }
            }

        # Also initialize centroids for all 35 alphanumeric classes using real ISL hand crops where available
        from CORE.sign_knowledge import ALPHANUMERIC_CLASSES, ALPHANUMERIC_METADATA, CLASS_TO_INDEX
        isl_hands_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "isl_hand_samples")
        for cls in ALPHANUMERIC_CLASSES:
            if cls in self.prototypes and self.prototypes[cls].get("metadata", {}).get("is_user_taught"):
                continue
            hand_file = os.path.join(isl_hands_dir, f"{cls}.png")
            if os.path.exists(hand_file):
                img = cv2.imread(hand_file)
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                tensor = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).float() / 255.0
                norm_tensor = (tensor - mean) / std
                with torch.no_grad():
                    _, emb = active_model.extract_features(norm_tensor)
                    norm_w = F.normalize(emb[0], p=2, dim=0)
            else:
                idx = CLASS_TO_INDEX[cls]
                with torch.no_grad():
                    w = active_model.classifier.weight[idx].clone()
                    norm_w = F.normalize(w, p=2, dim=0)
            meta = ALPHANUMERIC_METADATA.get(cls, {})
            self.prototypes[cls] = {
                "centroid": norm_w.cpu(),
                "samples": 3,
                "metadata": {
                    "category": "alphanumeric",
                    "hindi": meta.get("hindi", ""),
                    "handedness": meta.get("handedness", "one-handed")
                }
            }

    def add_prototype(
        self,
        word: str,
        feature_vector: Union[torch.Tensor, np.ndarray],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a new sample for a word, updating its online centroid.
        """
        if isinstance(feature_vector, np.ndarray):
            vec = torch.from_numpy(feature_vector).float()
        else:
            vec = feature_vector.float().clone()

        if vec.ndim > 1:
            vec = vec.view(-1)

        vec = F.normalize(vec, p=2, dim=0)
        norm_word = word.strip().upper()

        if norm_word in self.prototypes:
            # Running weighted centroid update
            curr = self.prototypes[norm_word]
            old_cent = curr["centroid"]
            n = curr["samples"]
            new_cent = F.normalize((old_cent * n + vec) / (n + 1), p=2, dim=0)
            curr["centroid"] = new_cent
            curr["samples"] = n + 1
            if metadata:
                curr["metadata"].update(metadata)
        else:
            meta = metadata or {}
            sign_info = get_sign_info(norm_word)
            if sign_info:
                meta.setdefault("hindi", sign_info.get("hindi", ""))
                meta.setdefault("handedness", sign_info.get("handedness", "one-handed"))
            self.prototypes[norm_word] = {
                "centroid": vec,
                "samples": 1,
                "metadata": meta
            }

    def remove_prototype(self, word: str) -> bool:
        """Remove a word from prototype memory."""
        norm_word = word.strip().upper()
        if norm_word in self.prototypes:
            del self.prototypes[norm_word]
            return True
        return False

    def match(
        self,
        query_vector: Union[torch.Tensor, np.ndarray],
        top_k: int = 5
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Calculate cosine similarity between query feature and all registered prototypes.
        Returns sorted list of (word, similarity_score, metadata).
        """
        if not self.prototypes:
            return []

        if isinstance(query_vector, np.ndarray):
            q = torch.from_numpy(query_vector).float()
        else:
            q = query_vector.float().clone()

        if q.ndim > 1:
            q = q.view(-1)

        q = F.normalize(q, p=2, dim=0)

        # Build tensor of all centroids
        words = list(self.prototypes.keys())
        centroids = torch.stack([self.prototypes[w]["centroid"] for w in words])  # (N, D)

        # Dot product of normalized vectors equals cosine similarity
        similarities = torch.mv(centroids, q).cpu().numpy()

        # Top-k indices
        k = min(top_k, len(words))
        top_indices = np.argsort(similarities)[::-1][:k]

        results = []
        for idx in top_indices:
            w = words[idx]
            sim = float(similarities[idx])
            meta = self.prototypes[w].get("metadata", {})
            results.append((w, sim, meta))

        return results

    def save(self, target_path: Optional[str] = None) -> None:
        """Persist prototypes to disk atomically and safely across concurrent Windows file handles."""
        path = target_path or self.memory_path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        tmp_path = path + f".tmp_{os.getpid()}"
        try:
            torch.save({
                "feature_dim": self.feature_dim,
                "prototypes": self.prototypes,
                "version": "1.0.0"
            }, tmp_path)
            if os.path.exists(tmp_path):
                os.replace(tmp_path, path)
        except Exception as e:
            try:
                torch.save({
                    "feature_dim": self.feature_dim,
                    "prototypes": self.prototypes,
                    "version": "1.0.0"
                }, path)
            except Exception as e2:
                print(f"[ISLMemoryTrainer] Warning: Could not persist memory file ({e2}). Memory retained in RAM.")

    def count(self) -> int:
        """Return total number of registered prototypes."""
        return len(self.prototypes)

    def reward_prediction(
        self,
        word: str,
        feature_vector: Union[torch.Tensor, np.ndarray],
        reward_weight: float = 1.0
    ) -> Dict[str, Any]:
        """
        Positive reinforcement: Strengthens prototype centroid for word
        by nudging it towards the confirmed feature vector.
        """
        if isinstance(feature_vector, np.ndarray):
            vec = torch.from_numpy(feature_vector).float()
        else:
            vec = feature_vector.float().clone()
        if vec.ndim > 1:
            vec = vec.view(-1)
        vec = F.normalize(vec, p=2, dim=0)

        norm_word = word.strip().upper()
        if norm_word in self.prototypes:
            curr = self.prototypes[norm_word]
            old_cent = curr["centroid"]
            n = curr.get("samples", 1)
            # Nudge centroid towards sample
            new_cent = F.normalize(old_cent + (reward_weight / max(1, n)) * vec, p=2, dim=0)
            curr["centroid"] = new_cent
            curr["samples"] = n + 1
            old_sim = float(torch.dot(old_cent, vec).item())
            new_sim = float(torch.dot(new_cent, vec).item())
        else:
            self.add_prototype(norm_word, vec)
            old_sim = 0.0
            new_sim = 1.0

        self.save()
        return {
            "status": "rewarded",
            "word": norm_word,
            "old_similarity": round(old_sim, 4),
            "new_similarity": round(new_sim, 4),
            "samples": self.prototypes[norm_word]["samples"]
        }

    def punish_and_correct(
        self,
        wrong_word: str,
        correct_word: str,
        feature_vector: Union[torch.Tensor, np.ndarray],
        punishment_factor: float = 0.6
    ) -> Dict[str, Any]:
        """
        Negative reinforcement & Instant Teaching:
        1. Severely punishes wrong_word by shifting its centroid AWAY from feature_vector,
           sharply reducing its cosine similarity for this gesture.
        2. Awards / registers correct_word with strong positive attraction towards feature_vector.
        3. Saves memory immediately so next query improves without manual model retraining.
        """
        if isinstance(feature_vector, np.ndarray):
            vec = torch.from_numpy(feature_vector).float()
        else:
            vec = feature_vector.float().clone()
        if vec.ndim > 1:
            vec = vec.view(-1)
        vec = F.normalize(vec, p=2, dim=0)

        norm_wrong = wrong_word.strip().upper()
        norm_correct = correct_word.strip().upper()

        wrong_old_sim = None
        wrong_new_sim = None

        # 1. Severely punish wrong word centroid
        if norm_wrong in self.prototypes:
            wrong_cent = self.prototypes[norm_wrong]["centroid"]
            wrong_old_sim = float(torch.dot(wrong_cent, vec).item())
            # Severely repel along the direction of this mistaken feature vector
            proj = torch.dot(wrong_cent, vec) * vec
            repelled = wrong_cent - (1.0 + punishment_factor) * proj
            if torch.norm(repelled) < 1e-6:
                repelled = -vec
            penalized_cent = F.normalize(repelled, p=2, dim=0)
            self.prototypes[norm_wrong]["centroid"] = penalized_cent
            wrong_new_sim = float(torch.dot(penalized_cent, vec).item())

        # 2. Reinforce / enroll correct word
        if norm_correct in self.prototypes:
            corr_curr = self.prototypes[norm_correct]
            corr_cent = corr_curr["centroid"]
            corr_old_sim = float(torch.dot(corr_cent, vec).item())
            # Strongly pull correct centroid towards this gesture feature
            boosted_cent = F.normalize(corr_cent + 2.0 * vec, p=2, dim=0)
            corr_curr["centroid"] = boosted_cent
            corr_curr["samples"] = corr_curr.get("samples", 1) + 1
            corr_curr.setdefault("metadata", {})["is_user_taught"] = True
            corr_new_sim = float(torch.dot(boosted_cent, vec).item())
        else:
            meta = {"is_user_taught": True}
            from CORE.sign_knowledge import get_sign_info
            info = get_sign_info(norm_correct)
            if info:
                meta.update({
                    "category": info.get("category", "custom"),
                    "hindi": info.get("hindi", ""),
                    "handedness": info.get("handedness", "one-handed")
                })
            self.prototypes[norm_correct] = {
                "centroid": vec,
                "samples": 3,
                "metadata": meta
            }
            corr_old_sim = 0.0
            corr_new_sim = 1.0

        self.save()

        return {
            "status": "punished_and_corrected",
            "wrong_word": norm_wrong,
            "wrong_old_similarity": round(wrong_old_sim, 4) if wrong_old_sim is not None else None,
            "wrong_new_similarity": round(wrong_new_sim, 4) if wrong_new_sim is not None else None,
            "correct_word": norm_correct,
            "correct_old_similarity": round(corr_old_sim, 4),
            "correct_new_similarity": round(corr_new_sim, 4),
            "total_prototypes": len(self.prototypes)
        }
