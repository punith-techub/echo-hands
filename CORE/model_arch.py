"""
ECHOHANDS - Neural Network Architecture
Dual-Brain Backbone with MobileNetV3-Small Pretrained Features,
512-dim embedding neck, 35-class Alphanumeric classifier head,
and built-in Stage 4 Grad-CAM activation hooks.
"""

import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
from typing import Tuple, Optional

LOCAL_PRETRAINED_WEIGHTS = os.path.join(
    os.path.expanduser("~"), ".cache", "torch", "hub", "checkpoints", "mobilenet_v3_small-047dcff4.pth"
)

class ISLNet(nn.Module):
    """
    High-Precision Tactical ISL Vision Backbone based on MobileNetV3-Small.
    Input: (B, 3, 224, 224)
    Activations: (B, 576, 7, 7) from final convolutional stage
    Embedding neck: (B, 512)
    Logits: (B, num_classes=35)
    """
    def __init__(self, num_classes: int = 35, embedding_dim: int = 512, pretrained: bool = True):
        super().__init__()
        self.embedding_dim = embedding_dim
        self.num_classes = num_classes

        # Base MobileNetV3-Small architecture
        base = models.mobilenet_v3_small(weights=None)
        if pretrained and os.path.exists(LOCAL_PRETRAINED_WEIGHTS):
            try:
                base.load_state_dict(torch.load(LOCAL_PRETRAINED_WEIGHTS, map_location="cpu"))
            except Exception as e:
                print(f"[ISLNet] Notice: Pretrained weights load warning: {e}")

        # Features: 13 stages (conv stem, inverted residuals)
        self.features = base.features
        # stage4 alias for Grad-CAM targeting the final conv layer
        self.stage4 = self.features[-1]

        # Spatial pooling
        self.pool = nn.AdaptiveAvgPool2d((1, 1))

        # 512-D Embedding Neck
        self.neck = nn.Sequential(
            nn.Linear(576, embedding_dim),
            nn.BatchNorm1d(embedding_dim),
            nn.Hardswish(),
            nn.Dropout(p=0.20)
        )

        # 35-class Alphanumeric Classifier Head
        self.classifier = nn.Linear(embedding_dim, num_classes)

        # Initialize neck & classifier heads cleanly
        self._init_head()

    def _init_head(self):
        for m in self.neck.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
        nn.init.normal_(self.classifier.weight, 0, 0.01)
        if self.classifier.bias is not None:
            nn.init.constant_(self.classifier.bias, 0)

    def extract_features(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through convolutional backbone and embedding neck.
        Returns:
            activations: feature map from stage4 (B, 576, 7, 7)
            embedding: L2-normalized 512-dim embedding (B, 512)
        """
        activations = self.features(x)  # (B, 576, 7, 7)
        pooled = self.pool(activations).flatten(1)  # (B, 576)
        emb = self.neck(pooled)  # (B, 512)
        norm_embedding = F.normalize(emb, p=2, dim=1)
        return activations, norm_embedding

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Full forward pass producing classification logits and normalized embeddings.
        Returns:
            logits: (B, num_classes)
            embedding: (B, 512)
        """
        activations = self.features(x)
        pooled = self.pool(activations).flatten(1)
        emb = self.neck(pooled)
        logits = self.classifier(emb)
        norm_embedding = F.normalize(emb, p=2, dim=1)
        return logits, norm_embedding
