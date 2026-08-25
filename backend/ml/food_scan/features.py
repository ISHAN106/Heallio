from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image


def extract_food_features(image_bytes: bytes) -> np.ndarray:
    image = Image.open(BytesIO(image_bytes)).convert("RGB").resize((224, 224))
    pixels = np.asarray(image, dtype=np.float32) / 255.0

    red = pixels[..., 0]
    green = pixels[..., 1]
    blue = pixels[..., 2]

    mean_rgb = pixels.mean(axis=(0, 1))
    std_rgb = pixels.std(axis=(0, 1))
    brightness = float(pixels.mean())
    saturation = float((np.max(pixels, axis=2) - np.min(pixels, axis=2)).mean())
    contrast = float(pixels.std())
    edge_h = float(np.abs(np.diff(pixels, axis=1)).mean())
    edge_v = float(np.abs(np.diff(pixels, axis=0)).mean())
    edge_density = (edge_h + edge_v) / 2.0
    warm_balance = float((red.mean() - blue.mean()) * 0.5 + 0.5)
    green_balance = float((green.mean() - ((red.mean() + blue.mean()) / 2.0)) * 0.8 + 0.5)
    gray = pixels.mean(axis=2)
    hist, _ = np.histogram(gray, bins=16, range=(0.0, 1.0), density=True)
    hist = hist / max(hist.sum(), 1e-6)
    entropy = float(-np.sum(hist * np.log2(hist + 1e-8)) / 4.0)
    aspect_ratio = float(min(image.width / max(image.height, 1), 3.0) / 3.0)

    hist_features: list[float] = []
    for channel in (red, green, blue):
        channel_hist, _ = np.histogram(channel, bins=6, range=(0.0, 1.0), density=True)
        channel_hist = channel_hist / max(channel_hist.sum(), 1e-6)
        hist_features.extend(float(value) for value in channel_hist)

    features = np.concatenate(
        [
            mean_rgb,
            std_rgb,
            np.array(
                [
                    brightness,
                    saturation,
                    contrast,
                    edge_density,
                    warm_balance,
                    green_balance,
                    entropy,
                    aspect_ratio,
                ],
                dtype=np.float32,
            ),
            np.array(hist_features, dtype=np.float32),
        ]
    )
    return np.clip(features, 0.0, 1.0)


def feature_names() -> list[str]:
    return [
        "mean_red",
        "mean_green",
        "mean_blue",
        "std_red",
        "std_green",
        "std_blue",
        "brightness",
        "saturation",
        "contrast",
        "edge_density",
        "warm_balance",
        "green_balance",
        "entropy",
        "aspect_ratio",
        "red_hist_0",
        "red_hist_1",
        "red_hist_2",
        "red_hist_3",
        "red_hist_4",
        "red_hist_5",
        "green_hist_0",
        "green_hist_1",
        "green_hist_2",
        "green_hist_3",
        "green_hist_4",
        "green_hist_5",
        "blue_hist_0",
        "blue_hist_1",
        "blue_hist_2",
        "blue_hist_3",
        "blue_hist_4",
        "blue_hist_5",
    ]
