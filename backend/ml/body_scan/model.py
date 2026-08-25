from __future__ import annotations

from io import BytesIO
from typing import Optional

from PIL import Image, UnidentifiedImageError

from .catalog import profile_for_label
from .cnn import cnn_artifacts_available, cnn_training_report, predict_with_cnn

MODEL_VERSION_CNN = "1-cnn"
MODEL_VERSION_HEURISTIC = "0-heuristic"

UNCERTAINTY_THRESHOLD = 0.35


def _prepare_image(image_bytes: bytes) -> bytes:
    try:
        image = Image.open(BytesIO(image_bytes))
        image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Please upload a valid image file.") from exc
    return image_bytes


def analyze_body_image(image_bytes: bytes, body_part: Optional[str] = None) -> dict:
    if not cnn_artifacts_available():
        # No trained CNN artifacts yet -- fall back to the deterministic heuristic
        # so the /scan/analyze endpoint keeps working during local dev/CI.
        from app.services.body_scan_model import analyze_body_image as analyze_body_image_heuristic

        return analyze_body_image_heuristic(image_bytes, body_part=body_part)

    image_bytes = _prepare_image(image_bytes)
    ranked = predict_with_cnn(image_bytes)
    training_report = cnn_training_report() or {}
    training_accuracy = training_report.get("val_accuracy")

    best_label, best_confidence = ranked[0]
    low_confidence = best_confidence < UNCERTAINTY_THRESHOLD

    predictions = [
        {"label": profile_for_label(label).display_name, "confidence": round(float(conf), 4)}
        for label, conf in ranked[:3]
    ]

    if low_confidence:
        display_label = "Uncertain visual finding"
        urgency_level = "review"
        summary = (
            "The image quality or visual pattern is not clear enough for a reliable estimate. "
            "Please retake in good lighting and from a closer, focused angle."
        )
        recommendation = (
            "Track symptoms, avoid self-diagnosis from this image alone, and consult a clinician if pain, "
            "swelling, fever, or worsening changes are present."
        )
    else:
        profile = profile_for_label(best_label)
        display_label = profile.display_name
        urgency_level = profile.urgency_level
        summary = profile.summary
        recommendation = profile.recommendation

    notes_confidence = f" ({int(round(best_confidence * 100))}% confidence)" if not low_confidence else ""

    return {
        "most_likely_condition": display_label,
        "confidence": round(float(best_confidence), 4),
        "predictions": predictions,
        "urgency_level": urgency_level,
        "summary": summary + notes_confidence,
        "recommendation": recommendation,
        "disclaimer": (
            "This is an AI-assisted visual screening result from a model trained on the DermNet dermatology "
            "dataset, not a medical diagnosis. Do not ignore urgent symptoms such as severe pain, breathing "
            "difficulty, heavy bleeding, rapid swelling, fever, confusion, or fainting."
        ),
        "body_part": body_part,
        "model_version": MODEL_VERSION_CNN,
        "training_accuracy": training_accuracy,
    }
