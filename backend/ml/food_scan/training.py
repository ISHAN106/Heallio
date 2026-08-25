from __future__ import annotations

import json
import os
from pathlib import Path

import joblib
import numpy as np
from PIL import Image, UnidentifiedImageError
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error
from sklearn.model_selection import train_test_split

from .catalog import FOOD_PROFILES, PROFILE_BY_KEY, profile_for_label
from .features import feature_names


BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "model", "food_scan_model.joblib")
REPORT_PATH = os.path.join(BASE_DIR, "model", "food_scan_training_report.json")
DATASET_DIR = os.path.join(BASE_DIR, "data", "food_dataset")
RANDOM_SEED = 42
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _feature_dim() -> int:
    return len(feature_names())


def _align_feature_vector(values: np.ndarray) -> np.ndarray:
    target_dim = _feature_dim()
    flat = np.asarray(values, dtype=np.float32).reshape(-1)
    if flat.size == target_dim:
        return np.clip(flat, 0.0, 1.0)
    if flat.size > target_dim:
        return np.clip(flat[:target_dim], 0.0, 1.0)
    return np.clip(np.pad(flat, (0, target_dim - flat.size), constant_values=0.0), 0.0, 1.0)


def _generate_center_from_profile(profile) -> np.ndarray:
    return _align_feature_vector(profile.feature_center)


def _load_directory_dataset(dataset_dir: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, dict]]:
    root = Path(dataset_dir)
    if not root.exists():
        return np.empty((0, _feature_dim()), dtype=np.float32), np.array([]), np.array([], dtype=np.float32), {}

    features: list[np.ndarray] = []
    labels: list[str] = []
    portions: list[float] = []
    class_profiles: dict[str, dict] = {}

    for class_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        profile = profile_for_label(class_dir.name)
        class_profiles[profile.key] = {
            "key": profile.key,
            "display_name": profile.display_name,
            "portion_label": profile.portion_label,
            "portion_grams": profile.portion_grams,
            "nutrition_per_100g": profile.nutrition_per_100g,
            "micronutrients_per_100g": profile.micronutrients_per_100g,
            "contents": profile.contents,
            "feature_noise": profile.feature_noise,
            "portion_noise": profile.portion_noise,
            "suggested_meal_type": profile.suggested_meal_type,
        }

        for image_path in sorted(class_dir.iterdir()):
            if image_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
                continue

            try:
                with Image.open(image_path) as image:
                    array = np.asarray(image.convert("RGB").resize((224, 224)), dtype=np.float32) / 255.0
            except (UnidentifiedImageError, OSError):
                continue

            from .features import extract_food_features

            feature_vector = extract_food_features(image_path.read_bytes())
            features.append(feature_vector)
            labels.append(profile.key)
            portions.append(float(profile.portion_grams))

    if not features:
        return np.empty((0, _feature_dim()), dtype=np.float32), np.array([]), np.array([], dtype=np.float32), {}

    return np.vstack(features), np.array(labels), np.array(portions, dtype=np.float32), class_profiles


def _generate_synthetic_dataset(samples_per_class: int = 400) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(RANDOM_SEED)
    x_rows: list[np.ndarray] = []
    class_labels: list[str] = []
    portion_targets: list[float] = []

    for profile in FOOD_PROFILES:
        center = _generate_center_from_profile(profile)
        for _ in range(samples_per_class):
            sample = center + rng.normal(0.0, profile.feature_noise, size=center.shape[0])
            sample = np.clip(sample, 0.0, 1.0)
            x_rows.append(sample.astype(np.float32))
            class_labels.append(profile.key)
            portion = rng.normal(profile.portion_grams, profile.portion_noise)
            portion_targets.append(float(max(60.0, portion)))

    return np.vstack(x_rows), np.array(class_labels), np.array(portion_targets, dtype=np.float32)


def train_food_scan_model(samples_per_class: int = 400) -> dict:
    features, class_labels, portion_targets, class_profiles = _load_directory_dataset(DATASET_DIR)
    dataset_source = "folder" if len(class_labels) else "synthetic"

    if not len(class_labels):
        features, class_labels, portion_targets = _generate_synthetic_dataset(samples_per_class=samples_per_class)
        class_profiles = {
            profile.key: {
                "key": profile.key,
                "display_name": profile.display_name,
                "portion_label": profile.portion_label,
                "portion_grams": profile.portion_grams,
                "nutrition_per_100g": profile.nutrition_per_100g,
                "micronutrients_per_100g": profile.micronutrients_per_100g,
                "contents": profile.contents,
                "feature_noise": profile.feature_noise,
                "portion_noise": profile.portion_noise,
                "suggested_meal_type": profile.suggested_meal_type,
            }
            for profile in FOOD_PROFILES
        }

    features = np.asarray([_align_feature_vector(vector) for vector in features], dtype=np.float32)
    x_train, x_test, y_train, y_test, portion_train, portion_test = train_test_split(
        features,
        class_labels,
        portion_targets,
        test_size=0.2,
        random_state=RANDOM_SEED,
        stratify=class_labels,
    )

    classifier = RandomForestClassifier(
        n_estimators=240,
        max_depth=14,
        min_samples_leaf=2,
        random_state=RANDOM_SEED,
        class_weight="balanced_subsample",
    )
    classifier.fit(x_train, y_train)

    regressor = RandomForestRegressor(
        n_estimators=220,
        max_depth=12,
        min_samples_leaf=2,
        random_state=RANDOM_SEED,
    )
    regressor.fit(x_train, portion_train)

    class_predictions = classifier.predict(x_test)
    portion_predictions = regressor.predict(x_test)

    report = {
        "feature_names": feature_names(),
        "classes": sorted(set(str(label) for label in class_labels)),
        "dataset_source": dataset_source,
        "classifier_accuracy": round(float(accuracy_score(y_test, class_predictions)), 4),
        "portion_mae_grams": round(float(mean_absolute_error(portion_test, portion_predictions)), 2),
        "samples_per_class": samples_per_class,
        "profiles": list(class_profiles.values()),
    }

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(
        {
            "version": 1,
            "classifier": classifier,
            "regressor": regressor,
            "report": report,
            "class_profiles": class_profiles,
        },
        MODEL_PATH,
    )

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    result = train_food_scan_model()
    print(json.dumps(result, indent=2))
