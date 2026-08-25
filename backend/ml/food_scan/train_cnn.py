from __future__ import annotations

import json
import os
import random
from collections import Counter

import torch
from PIL import Image, UnidentifiedImageError
from torch import nn
from torch.utils.data import DataLoader, Dataset, Subset, WeightedRandomSampler

from .catalog import profile_for_label
from .cnn import (
    CNN_CLASSES_PATH,
    CNN_MODEL_PATH,
    CNN_REPORT_PATH,
    FoodCNN,
    build_inference_transform,
    build_train_transform,
)

BASE_DIR = os.path.dirname(__file__)
DATASET_DIR = os.path.join(BASE_DIR, "data", "food_dataset")
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
RANDOM_SEED = 42
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class FoodImageDataset(Dataset):
    def __init__(self, samples: list[tuple[str, int]], portions: list[float], transform):
        self.samples = samples
        self.portions = portions
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int):
        path, label = self.samples[index]
        with Image.open(path) as image:
            tensor = self.transform(image.convert("RGB"))
        return tensor, label, self.portions[index]


def _discover_samples() -> tuple[list[tuple[str, int]], list[float], list[str]]:
    root = DATASET_DIR
    if not os.path.isdir(root):
        raise FileNotFoundError(
            f"No dataset found at {root}. Create one subfolder per food class containing its photos, "
            "e.g. data/food_dataset/butter_chicken/*.jpg, data/food_dataset/margherita_pizza/*.jpg"
        )

    class_dirs = sorted(name for name in os.listdir(root) if os.path.isdir(os.path.join(root, name)))
    if len(class_dirs) < 2:
        raise ValueError("Need at least 2 class subfolders with images to train a classifier.")

    samples: list[tuple[str, int]] = []
    portions: list[float] = []
    for class_index, class_name in enumerate(class_dirs):
        class_dir = os.path.join(root, class_name)
        profile = profile_for_label(class_name)
        count = 0
        for filename in sorted(os.listdir(class_dir)):
            if os.path.splitext(filename)[1].lower() not in SUPPORTED_EXTENSIONS:
                continue
            path = os.path.join(class_dir, filename)
            try:
                with Image.open(path) as image:
                    image.verify()
            except (UnidentifiedImageError, OSError):
                continue
            samples.append((path, class_index))
            portions.append(float(profile.portion_grams))
            count += 1
        if count == 0:
            raise ValueError(f"Class folder '{class_name}' has no readable images.")

    return samples, portions, class_dirs


def _stratified_split(samples: list[tuple[str, int]], val_ratio: float = 0.15) -> tuple[list[int], list[int]]:
    rng = random.Random(RANDOM_SEED)
    by_class: dict[int, list[int]] = {}
    for index, (_, label) in enumerate(samples):
        by_class.setdefault(label, []).append(index)

    train_indices: list[int] = []
    val_indices: list[int] = []
    for indices in by_class.values():
        indices = indices[:]
        rng.shuffle(indices)
        n_val = max(1, int(len(indices) * val_ratio)) if len(indices) > 4 else 0
        val_indices.extend(indices[:n_val])
        train_indices.extend(indices[n_val:])
    return train_indices, val_indices


def train_food_cnn(
    epochs_frozen: int = 3,
    epochs_finetune: int = 10,
    batch_size: int = 32,
    lr_head: float = 1e-3,
    lr_finetune: float = 1e-4,
    weight_decay: float = 1e-4,
    sampler_cap: int | None = 15000,
    patience: int = 4,
) -> dict:
    torch.manual_seed(RANDOM_SEED)
    samples, portions, class_names = _discover_samples()
    num_classes = len(class_names)
    train_idx, val_idx = _stratified_split(samples)

    train_dataset = FoodImageDataset(samples, portions, build_train_transform())
    eval_dataset = FoodImageDataset(samples, portions, build_inference_transform())

    # Oversample minority classes so each of their (few) photos gets seen multiple
    # times per epoch, each time with a different random augmentation -- this buys
    # more effective visual diversity out of a fixed, imbalanced set of photos.
    # (Loss-weighting alone still only sees each minority image once per epoch.)
    train_labels = [samples[i][1] for i in train_idx]
    train_class_counts = Counter(train_labels)
    sample_weights = [1.0 / train_class_counts[label] for label in train_labels]
    num_train_samples = min(len(train_idx), sampler_cap) if sampler_cap else len(train_idx)
    train_sampler = WeightedRandomSampler(sample_weights, num_samples=num_train_samples, replacement=True)

    train_loader = DataLoader(
        Subset(train_dataset, train_idx), batch_size=batch_size, sampler=train_sampler, num_workers=0
    )
    val_loader = (
        DataLoader(Subset(eval_dataset, val_idx), batch_size=batch_size, shuffle=False, num_workers=0)
        if val_idx
        else None
    )

    model = FoodCNN(num_classes=num_classes).to(DEVICE)

    # The sampler above already balances class exposure, so the loss itself stays
    # unweighted (stacking both would overcorrect and hurt majority-class accuracy).
    classification_loss_fn = nn.CrossEntropyLoss(label_smoothing=0.05)
    portion_loss_fn = nn.SmoothL1Loss()

    def run_epoch(optimizer=None, loader=None):
        is_train = optimizer is not None
        model.train(is_train)
        loader = loader if loader is not None else (train_loader if is_train else val_loader)
        if loader is None:
            return None

        total_loss = 0.0
        correct = 0
        count = 0
        portion_abs_error = 0.0
        class_correct = [0] * num_classes
        class_total = [0] * num_classes
        with torch.set_grad_enabled(is_train):
            for images, labels, portion_targets in loader:
                images = images.to(DEVICE)
                labels = labels.to(DEVICE)
                portion_targets = portion_targets.to(DEVICE).float()

                class_logits, portion_pred = model(images)
                loss = classification_loss_fn(class_logits, labels) + 0.001 * portion_loss_fn(
                    portion_pred, portion_targets
                )

                if is_train:
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()

                preds = class_logits.argmax(dim=1)
                total_loss += loss.item() * images.size(0)
                correct += (preds == labels).sum().item()
                portion_abs_error += (portion_pred - portion_targets).abs().sum().item()
                count += images.size(0)
                for label, pred in zip(labels.tolist(), preds.tolist()):
                    class_total[label] += 1
                    if pred == label:
                        class_correct[label] += 1

        seen_classes = [i for i in range(num_classes) if class_total[i] > 0]
        macro_accuracy = (
            sum(class_correct[i] / class_total[i] for i in seen_classes) / len(seen_classes)
            if seen_classes
            else 0.0
        )

        return {
            "loss": total_loss / max(count, 1),
            "accuracy": correct / max(count, 1),
            "macro_accuracy": macro_accuracy,
            "portion_mae_grams": portion_abs_error / max(count, 1),
        }

    print(
        f"[train_cnn] {len(class_names)} classes, {len(samples)} images "
        f"({len(train_idx)} train / {len(val_idx)} val), device={DEVICE}",
        flush=True,
    )

    # Phase 1: warm up the two heads with the pretrained backbone frozen.
    model.set_backbone_trainable(False)
    head_params = list(model.classifier_head.parameters()) + list(model.portion_head.parameters())
    optimizer = torch.optim.Adam(head_params, lr=lr_head, weight_decay=weight_decay)
    for epoch in range(epochs_frozen):
        metrics = run_epoch(optimizer, train_loader)
        print(
            f"[train_cnn] warmup epoch {epoch + 1}/{epochs_frozen} "
            f"train_loss={metrics['loss']:.4f} train_acc={metrics['accuracy']:.4f} "
            f"train_macro_acc={metrics['macro_accuracy']:.4f}",
            flush=True,
        )

    # Phase 2: fine-tune the whole network at a lower learning rate. The checkpoint is
    # selected by macro-averaged (per-class, unweighted) val accuracy rather than the
    # size-weighted overall accuracy, since the latter is dominated by the handful of
    # 1000+ image classes and can look good while the long tail is still failing.
    model.set_backbone_trainable(True)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr_finetune, weight_decay=weight_decay)
    best_macro_accuracy = -1.0
    best_val_accuracy = -1.0
    best_state = None
    patience_counter = 0
    for epoch in range(epochs_finetune):
        train_metrics = run_epoch(optimizer, train_loader)
        val_metrics = run_epoch(None, val_loader)
        val_str = (
            f"val_loss={val_metrics['loss']:.4f} val_acc={val_metrics['accuracy']:.4f} "
            f"val_macro_acc={val_metrics['macro_accuracy']:.4f} "
            f"val_portion_mae={val_metrics['portion_mae_grams']:.1f}g"
            if val_metrics
            else "val=n/a"
        )
        print(
            f"[train_cnn] finetune epoch {epoch + 1}/{epochs_finetune} "
            f"train_loss={train_metrics['loss']:.4f} train_acc={train_metrics['accuracy']:.4f} {val_str}",
            flush=True,
        )
        if val_metrics and val_metrics["macro_accuracy"] > best_macro_accuracy:
            best_macro_accuracy = val_metrics["macro_accuracy"]
            best_val_accuracy = val_metrics["accuracy"]
            best_state = {key: value.clone() for key, value in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"[train_cnn] early stopping: no macro-accuracy improvement for {patience} epochs", flush=True)
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    final_val = run_epoch(None, val_loader) or {}
    print(
        f"[train_cnn] done. best_val_accuracy={best_val_accuracy:.4f} best_macro_accuracy={best_macro_accuracy:.4f}",
        flush=True,
    )

    report = {
        "classes": class_names,
        "num_images": len(samples),
        "samples_per_class": dict(Counter(class_names[label] for _, label in samples)),
        "val_accuracy": round(final_val.get("accuracy", 0.0), 4),
        "val_macro_accuracy": round(final_val.get("macro_accuracy", 0.0), 4),
        "val_portion_mae_grams": round(final_val.get("portion_mae_grams", 0.0), 2),
        "epochs_frozen": epochs_frozen,
        "epochs_finetune": epochs_finetune,
    }

    # Never let a worse run (e.g. a short smoke test) clobber a better saved checkpoint.
    if os.path.exists(CNN_REPORT_PATH):
        with open(CNN_REPORT_PATH, "r", encoding="utf-8") as f:
            previous_accuracy = json.load(f).get("val_macro_accuracy", -1.0)
        if report["val_macro_accuracy"] <= previous_accuracy:
            print(
                f"[train_cnn] skipping save: new val_macro_accuracy={report['val_macro_accuracy']:.4f} "
                f"does not beat saved {previous_accuracy:.4f}",
                flush=True,
            )
            return report

    os.makedirs(os.path.dirname(CNN_MODEL_PATH), exist_ok=True)
    torch.save(model.state_dict(), CNN_MODEL_PATH)
    with open(CNN_CLASSES_PATH, "w", encoding="utf-8") as f:
        json.dump(class_names, f, indent=2)
    with open(CNN_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    result = train_food_cnn()
    print(json.dumps(result, indent=2))
