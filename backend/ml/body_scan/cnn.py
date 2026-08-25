from __future__ import annotations

import json
import os
from functools import lru_cache
from io import BytesIO

from PIL import Image

try:
    import torch
    from torch import nn
    from torchvision import models, transforms

    TORCH_AVAILABLE = True
except ImportError:  # torch/torchvision not installed yet
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]
    models = None  # type: ignore[assignment]
    transforms = None  # type: ignore[assignment]
    TORCH_AVAILABLE = False

BASE_DIR = os.path.dirname(__file__)
CNN_MODEL_PATH = os.path.join(BASE_DIR, "model", "body_scan_cnn.pt")
CNN_CLASSES_PATH = os.path.join(BASE_DIR, "model", "body_scan_cnn_classes.json")
CNN_REPORT_PATH = os.path.join(BASE_DIR, "model", "body_scan_cnn_training_report.json")

IMAGE_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


if TORCH_AVAILABLE:

    class BodyScanCNN(nn.Module):
        """MobileNetV2 backbone (ImageNet transfer learning) with a skin-condition
        classification head."""

        def __init__(self, num_classes: int):
            super().__init__()
            backbone = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
            self.features = backbone.features
            self.pool = nn.AdaptiveAvgPool2d(1)
            feature_dim = backbone.last_channel
            self.dropout = nn.Dropout(0.3)
            self.classifier_head = nn.Linear(feature_dim, num_classes)

        def forward(self, x):
            x = self.features(x)
            x = self.pool(x).flatten(1)
            x = self.dropout(x)
            return self.classifier_head(x)

        def set_backbone_trainable(self, trainable: bool) -> None:
            for param in self.features.parameters():
                param.requires_grad = trainable

    def build_inference_transform():
        return transforms.Compose(
            [
                transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
                transforms.ToTensor(),
                transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            ]
        )

    def build_train_transform():
        return transforms.Compose(
            [
                transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.8, 1.0)),
                transforms.RandomHorizontalFlip(),
                transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.03),
                transforms.RandomRotation(10),
                transforms.ToTensor(),
                transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
                transforms.RandomErasing(p=0.2, scale=(0.02, 0.1)),
            ]
        )


def cnn_artifacts_available() -> bool:
    if not TORCH_AVAILABLE:
        return False
    return os.path.exists(CNN_MODEL_PATH) and os.path.exists(CNN_CLASSES_PATH)


def cnn_training_report() -> dict | None:
    if not os.path.exists(CNN_REPORT_PATH):
        return None
    with open(CNN_REPORT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_cnn():
    with open(CNN_CLASSES_PATH, "r", encoding="utf-8") as f:
        class_names = json.load(f)

    model = BodyScanCNN(num_classes=len(class_names))
    state = torch.load(CNN_MODEL_PATH, map_location="cpu")
    model.load_state_dict(state)
    model.eval()
    return model, class_names, build_inference_transform()


def predict_with_cnn(image_bytes: bytes) -> list[tuple[str, float]]:
    """Returns ranked [(class_slug, probability), ...] sorted by probability desc."""
    if not TORCH_AVAILABLE:
        raise RuntimeError("torch/torchvision are not installed; cannot run the CNN body scan model.")

    model, class_names, transform = _load_cnn()
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    tensor = transform(image).unsqueeze(0)

    with torch.no_grad():
        logits = model(tensor)
        probabilities = torch.softmax(logits, dim=1)[0]

    return sorted(zip(class_names, probabilities.tolist()), key=lambda item: item[1], reverse=True)
