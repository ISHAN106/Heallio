"""One-off script: download the DermNet dermatology dataset from Hugging Face
(WahajRaza/Dermnet, a mirror of the Kaggle DermNet dataset -- 23 classes,
~13.2k train / ~2.3k test images) and materialize it as one folder per class,
matching the layout ml/food_scan/data/food_dataset already uses so the same
kind of training pipeline can discover it.

Run once with: python -m ml.body_scan.prepare_dataset
"""

from __future__ import annotations

import os
import re

from datasets import load_dataset

BASE_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "dermnet")


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    dataset = load_dataset("WahajRaza/Dermnet")
    class_names = dataset["train"].features["label"].names

    counters = {name: 0 for name in class_names}
    for split in ("train", "test"):
        for example in dataset[split]:
            label_name = class_names[example["label"]]
            slug = _slugify(label_name)
            class_dir = os.path.join(OUTPUT_DIR, slug)
            os.makedirs(class_dir, exist_ok=True)

            counters[label_name] += 1
            image = example["image"].convert("RGB")
            path = os.path.join(class_dir, f"{counters[label_name]:05d}.jpg")
            image.save(path, format="JPEG", quality=90)

        print(f"[prepare_dataset] finished split={split}", flush=True)

    total = sum(counters.values())
    print(f"[prepare_dataset] done. {total} images across {len(class_names)} classes -> {OUTPUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
