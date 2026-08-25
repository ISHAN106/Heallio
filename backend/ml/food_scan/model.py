from __future__ import annotations

from functools import lru_cache
from io import BytesIO
import os
from typing import Any

import joblib
from PIL import Image, UnidentifiedImageError

from .catalog import FoodProfile, PROFILE_BY_KEY, humanize_label, profile_for_label
from .cnn import cnn_artifacts_available, cnn_training_report, predict_with_cnn
from .features import extract_food_features
from .training import MODEL_PATH, train_food_scan_model

MODEL_VERSION_RF = "1"
MODEL_VERSION_CNN = "2-cnn"


def _format_percentage(value: float) -> str:
    return f"{max(0.0, min(value, 100.0)):.0f}%"


def _estimate_amount(profile_key: str, grams: float) -> str:
    profile = PROFILE_BY_KEY.get(profile_key) or profile_for_label(profile_key)
    if grams <= 0:
        grams = profile.portion_grams
    return f"{profile.portion_label} (~{int(round(grams))} g)"


def _scale_nutrients(profile: FoodProfile, grams: float) -> dict[str, int]:
    scale = grams / 100.0
    nutrients = profile.nutrition_per_100g
    return {
        "calories": int(round(nutrients["calories"] * scale)),
        "carbs": int(round(nutrients["carbs"] * scale)),
        "protein": int(round(nutrients["protein"] * scale)),
        "fat": int(round(nutrients["fat"] * scale)),
        "fiber": int(round(nutrients["fiber"] * scale)),
        "sugar": int(round(nutrients["sugar"] * scale)),
    }


def _scale_micronutrients(profile: FoodProfile, grams: float) -> dict[str, str]:
    scale = grams / 100.0
    return {
        name: _format_percentage(amount * scale)
        for name, amount in profile.micronutrients_per_100g.items()
    }


def _profile_from_bundle(label: str, bundle: dict[str, Any]) -> FoodProfile:
    class_profiles = bundle.get("class_profiles", {})
    raw_profile = class_profiles.get(label)
    if isinstance(raw_profile, dict):
        return FoodProfile(
            key=raw_profile.get("key", label),
            display_name=raw_profile.get("display_name", humanize_label(label)),
            portion_label=raw_profile.get("portion_label", "1 serving"),
            portion_grams=float(raw_profile.get("portion_grams", 200.0)),
            nutrition_per_100g={
                key: float(value)
                for key, value in (raw_profile.get("nutrition_per_100g") or {}).items()
            },
            micronutrients_per_100g={
                key: float(value)
                for key, value in (raw_profile.get("micronutrients_per_100g") or {}).items()
            },
            contents=[str(item) for item in raw_profile.get("contents", [])],
            feature_center=profile_for_label(label).feature_center,
            feature_noise=float(raw_profile.get("feature_noise", 0.08)),
            portion_noise=float(raw_profile.get("portion_noise", 24.0)),
            suggested_meal_type=raw_profile.get("suggested_meal_type", "lunch"),
        )

    if label in PROFILE_BY_KEY:
        return PROFILE_BY_KEY[label]

    return profile_for_label(label)


@lru_cache(maxsize=1)
def load_model_bundle() -> dict[str, Any]:
    if not os.path.exists(MODEL_PATH):
        train_food_scan_model()
    bundle = joblib.load(MODEL_PATH)
    return bundle


def _prepare_image(image_bytes: bytes) -> bytes:
    try:
        image = Image.open(BytesIO(image_bytes))
        image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Please upload a valid image file.") from exc
    return image_bytes


def _predict_with_cnn(image_bytes: bytes) -> tuple[list[tuple[str, float]], float, float | None, str]:
    ranked, grams = predict_with_cnn(image_bytes)
    report = cnn_training_report() or {}
    return ranked, grams, report.get("val_accuracy"), MODEL_VERSION_CNN


def _predict_with_random_forest(image_bytes: bytes) -> tuple[list[tuple[str, float]], float, float | None, str]:
    bundle = load_model_bundle()
    classifier = bundle["classifier"]
    regressor = bundle["regressor"]
    report = bundle.get("report", {})

    features = extract_food_features(image_bytes).reshape(1, -1)
    probabilities = classifier.predict_proba(features)[0]
    class_labels = list(classifier.classes_)
    ranked = sorted(zip(class_labels, probabilities), key=lambda item: item[1], reverse=True)
    grams = max(60.0, float(regressor.predict(features)[0]))

    return ranked, grams, report.get("classifier_accuracy"), MODEL_VERSION_RF


def analyze_food_image(image_bytes: bytes, meal_type: str | None = None, hint: str | None = None) -> dict[str, Any]:
    image_bytes = _prepare_image(image_bytes)

    if cnn_artifacts_available():
        ranked, grams, training_accuracy, model_version = _predict_with_cnn(image_bytes)
        bundle = None
    else:
        ranked, grams, training_accuracy, model_version = _predict_with_random_forest(image_bytes)
        bundle = load_model_bundle()

    predicted_key = ranked[0][0]
    confidence = float(ranked[0][1])

    profile = _profile_from_bundle(predicted_key, bundle) if bundle is not None else profile_for_label(predicted_key)
    nutrients = _scale_nutrients(profile, grams)
    micronutrients = _scale_micronutrients(profile, grams)

    if hint:
        hint_lower = hint.lower().strip()
        if hint_lower and hint_lower in profile.display_name.lower():
            confidence = min(0.99, confidence + 0.03)

    def _display_name(label: str) -> str:
        if bundle is not None:
            return _profile_from_bundle(label, bundle).display_name
        return profile_for_label(label).display_name

    predictions = [
        {"label": _display_name(label), "confidence": round(float(score), 4)}
        for label, score in ranked[:3]
    ]

    amount = _estimate_amount(predicted_key, grams)
    meal_type_value = (meal_type or profile.suggested_meal_type).strip().lower()

    model_description = (
        "a CNN vision classifier (transfer-learned on real food photos)"
        if model_version == MODEL_VERSION_CNN
        else "a trained vision classifier and portion regressor"
    )
    notes = (
        f"Estimated from a food photo using {model_description}. "
        f"The predicted class is {profile.display_name.lower()} with {int(round(confidence * 100))}% confidence."
    )
    if confidence < 0.65:
        notes += " Confidence is moderate, so portion and nutrition values should be treated as approximate."

    return {
        "meal_type": meal_type_value,
        "predicted_food": profile.display_name,
        "amount": amount,
        "serving_size": f"About {int(round(grams))} g",
        "estimated_grams": round(grams, 1),
        "confidence": round(confidence, 4),
        "calories": nutrients["calories"],
        "carbs": nutrients["carbs"],
        "protein": nutrients["protein"],
        "fat": nutrients["fat"],
        "fiber": nutrients["fiber"],
        "sugar": nutrients["sugar"],
        "micronutrients": [
            {"name": name, "amount": amount} for name, amount in micronutrients.items()
        ],
        "contents": profile.contents,
        "predictions": predictions,
        "notes": notes,
        "model_version": model_version,
        "training_accuracy": training_accuracy,
        "scanned_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
