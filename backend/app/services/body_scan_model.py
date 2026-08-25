from __future__ import annotations

from io import BytesIO
from typing import Optional

import numpy as np
from PIL import Image


_PROTOTYPES = {
    "Possible inflammation or rash": np.array([0.78, 0.30, 0.28, 0.55], dtype=np.float32),
    "Possible bruise or discoloration": np.array([0.35, 0.62, 0.24, 0.42], dtype=np.float32),
    "Possible cut or abrasion": np.array([0.70, 0.45, 0.72, 0.58], dtype=np.float32),
    "No obvious visual issue": np.array([0.40, 0.38, 0.20, 0.40], dtype=np.float32),
}


def _softmax(scores: list[float]) -> list[float]:
    arr = np.array(scores, dtype=np.float32)
    arr = arr - np.max(arr)
    exp = np.exp(arr)
    probs = exp / np.sum(exp)
    return [float(x) for x in probs]


def _extract_features(image_bytes: bytes) -> np.ndarray:
    image = Image.open(BytesIO(image_bytes)).convert("RGB").resize((224, 224))
    pixels = np.asarray(image, dtype=np.float32) / 255.0

    red = pixels[..., 0]
    green = pixels[..., 1]
    blue = pixels[..., 2]

    # Feature 1: redness tendency
    redness = np.clip(((red - (green + blue) / 2.0).mean() * 3.0) + 0.5, 0.0, 1.0)

    # Feature 2: overall darkness
    darkness = np.clip(1.0 - pixels.mean(), 0.0, 1.0)

    # Feature 3: texture/edge roughness
    edge_h = np.abs(np.diff(pixels, axis=1)).mean()
    edge_v = np.abs(np.diff(pixels, axis=0)).mean()
    texture = np.clip((edge_h + edge_v) * 4.0, 0.0, 1.0)

    # Feature 4: saturation estimate
    max_rgb = np.max(pixels, axis=2)
    min_rgb = np.min(pixels, axis=2)
    saturation = np.clip((max_rgb - min_rgb).mean() * 2.0, 0.0, 1.0)

    return np.array([redness, darkness, texture, saturation], dtype=np.float32)


def analyze_body_image(image_bytes: bytes, body_part: Optional[str] = None) -> dict:
    features = _extract_features(image_bytes)

    labels = list(_PROTOTYPES.keys())
    scores = []
    for label in labels:
        distance = np.linalg.norm(features - _PROTOTYPES[label])
        scores.append(float(-distance))

    probs = _softmax(scores)
    ranked = sorted(zip(labels, probs), key=lambda x: x[1], reverse=True)
    predictions = [
        {
            "label": label,
            "confidence": round(conf, 4),
        }
        for label, conf in ranked[:3]
    ]

    best_label, best_confidence = ranked[0]
    uncertainty_threshold = 0.55
    low_confidence = best_confidence < uncertainty_threshold

    if low_confidence:
        summary = (
            "The image quality or visual pattern is not clear enough for a reliable estimate. "
            "Please retake in good lighting and from a closer, focused angle."
        )
        recommendation = (
            "Track symptoms, avoid self-diagnosis from this image alone, and consult a clinician if pain, "
            "swelling, fever, or worsening changes are present."
        )
        urgency_level = "review"
        best_label = "Uncertain visual finding"
    else:
        if best_label == "Possible cut or abrasion":
            urgency_level = "moderate" if features[2] > 0.65 else "review"
            summary = "The image pattern may be consistent with a superficial wound or abrasion."
            recommendation = (
                "Clean the area gently, keep it dry, and monitor for redness spread, pus, strong pain, "
                "or fever. Seek medical care if any warning signs appear."
            )
        elif best_label == "Possible inflammation or rash":
            urgency_level = "review"
            summary = "The image pattern may suggest irritation or inflammatory skin change."
            recommendation = (
                "Avoid possible irritants, monitor progression over 24 to 48 hours, and consult a clinician "
                "if symptoms worsen, spread quickly, or are associated with breathing issues."
            )
        elif best_label == "Possible bruise or discoloration":
            urgency_level = "low"
            summary = "The image pattern may suggest discoloration similar to bruising."
            recommendation = (
                "Observe for pain severity, swelling, and movement limitation. Seek care for severe pain, "
                "rapid expansion, or repeated unexplained bruising."
            )
        else:
            urgency_level = "low"
            summary = "No obvious high-risk visual pattern was detected from this single image."
            recommendation = (
                "Continue monitoring. If symptoms persist, worsen, or you feel unwell, seek professional evaluation."
            )

    return {
        "most_likely_condition": best_label,
        "confidence": round(float(best_confidence), 4),
        "predictions": predictions,
        "urgency_level": urgency_level,
        "summary": summary,
        "recommendation": recommendation,
        "disclaimer": (
            "This is an AI-assisted visual screening result, not a medical diagnosis. "
            "Do not ignore urgent symptoms such as severe pain, breathing difficulty, heavy bleeding, "
            "rapid swelling, fever, confusion, or fainting."
        ),
        "body_part": body_part,
    }
