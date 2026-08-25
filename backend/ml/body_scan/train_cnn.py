from __future__ import annotations

import json
import os
import random
from collections import Counter

import torch
from PIL import Image, UnidentifiedImageError
from torch import nn
from torch.utils.data import DataLoader, Dataset, Subset, WeightedRandomSampler

from .cnn import (
    CNN_CLASSES_PATH,
    CNN_MODEL_PATH,
    CNN_REPORT_PATH,
    BodyScanCNN,
    build_inference_transform,
    build_train_transform,
)

BASE_DIR = os.path.dirname(__file__)
DATASET_DIR = os.path.join(BASE_DIR, "data", "dermnet")
CHECKPOINT_PATH = os.path.join(BASE_DIR, "model", "body_scan_cnn_checkpoint.pt")
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
RANDOM_SEED = 42
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class SkinImageDataset(Dataset):
    def __init__(self, samples: list[tuple[str, int]], transform):
        self.samples = samples
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int):
        path, label = self.samples[index]
        with Image.open(path) as image:
            tensor = self.transform(image.convert("RGB"))
        return tensor, label


def _discover_samples() -> tuple[list[tuple[str, int]], list[str]]:
    root = DATASET_DIR
    if not os.path.isdir(root):
        raise FileNotFoundError(
            f"No dataset found at {root}. Run `python -m ml.body_scan.prepare_dataset` first "
            "to download and materialize the DermNet dataset."
        )

    class_dirs = sorted(name for name in os.listdir(root) if os.path.isdir(os.path.join(root, name)))
    if len(class_dirs) < 2:
        raise ValueError("Need at least 2 class subfolders with images to train a classifier.")

    samples: list[tuple[str, int]] = []
    for class_index, class_name in enumerate(class_dirs):
        class_dir = os.path.join(root, class_name)
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
            count += 1
        if count == 0:
            raise ValueError(f"Class folder '{class_name}' has no readable images.")

    return samples, class_dirs


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


def train_body_scan_cnn(
    epochs_frozen: int = 2,
    epochs_finetune: int = 8,
    batch_size: int = 32,
    lr_head: float = 1e-3,
    lr_finetune: float = 1e-4,
    weight_decay: float = 1e-4,
    sampler_cap: int | None = 12000,
    patience: int = 3,
) -> dict:
    torch.manual_seed(RANDOM_SEED)
    samples, class_names = _discover_samples()
    num_classes = len(class_names)
    train_idx, val_idx = _stratified_split(samples)

    train_dataset = SkinImageDataset(samples, build_train_transform())
    eval_dataset = SkinImageDataset(samples, build_inference_transform())

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

    model = BodyScanCNN(num_classes=num_classes).to(DEVICE)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.05)

    # Training is CPU-only and slow enough that a single run can outlive the
    # process lifetime of whatever is launching it, so checkpoint after every
    # finetune epoch and resume from there instead of restarting from scratch.
    checkpoint = None
    if os.path.exists(CHECKPOINT_PATH):
        checkpoint = torch.load(CHECKPOINT_PATH, map_location=DEVICE)
        if checkpoint.get("class_names") != class_names:
            print("[train_cnn] checkpoint class list mismatch, ignoring checkpoint", flush=True)
            checkpoint = None

    def run_epoch(optimizer=None, loader=None):
        is_train = optimizer is not None
        model.train(is_train)
        loader = loader if loader is not None else (train_loader if is_train else val_loader)
        if loader is None:
            return None

        total_loss = 0.0
        correct = 0
        count = 0
        class_correct = [0] * num_classes
        class_total = [0] * num_classes
        with torch.set_grad_enabled(is_train):
            for images, labels in loader:
                images = images.to(DEVICE)
                labels = labels.to(DEVICE)

                logits = model(images)
                loss = loss_fn(logits, labels)

                if is_train:
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()

                preds = logits.argmax(dim=1)
                total_loss += loss.item() * images.size(0)
                correct += (preds == labels).sum().item()
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
        }

    print(
        f"[train_cnn] {len(class_names)} classes, {len(samples)} images "
        f"({len(train_idx)} train / {len(val_idx)} val), device={DEVICE}",
        flush=True,
    )

    start_epoch = 0
    best_macro_accuracy = -1.0
    best_val_accuracy = -1.0
    best_state = None
    patience_counter = 0

    if checkpoint is not None:
        model.set_backbone_trainable(True)
        model.load_state_dict(checkpoint["model_state"])
        optimizer = torch.optim.Adam(model.parameters(), lr=lr_finetune, weight_decay=weight_decay)
        optimizer.load_state_dict(checkpoint["optimizer_state"])
        start_epoch = checkpoint["epoch"] + 1
        best_macro_accuracy = checkpoint["best_macro_accuracy"]
        best_val_accuracy = checkpoint["best_val_accuracy"]
        best_state = checkpoint["best_state"]
        patience_counter = checkpoint["patience_counter"]
        print(f"[train_cnn] resumed from checkpoint at finetune epoch {start_epoch}", flush=True)
    else:
        model.set_backbone_trainable(False)
        optimizer = torch.optim.Adam(model.classifier_head.parameters(), lr=lr_head, weight_decay=weight_decay)
        for epoch in range(epochs_frozen):
            metrics = run_epoch(optimizer, train_loader)
            print(
                f"[train_cnn] warmup epoch {epoch + 1}/{epochs_frozen} "
                f"train_loss={metrics['loss']:.4f} train_acc={metrics['accuracy']:.4f} "
                f"train_macro_acc={metrics['macro_accuracy']:.4f}",
                flush=True,
            )

        model.set_backbone_trainable(True)
        optimizer = torch.optim.Adam(model.parameters(), lr=lr_finetune, weight_decay=weight_decay)

    for epoch in range(start_epoch, epochs_finetune):
        train_metrics = run_epoch(optimizer, train_loader)
        val_metrics = run_epoch(None, val_loader)
        val_str = (
            f"val_loss={val_metrics['loss']:.4f} val_acc={val_metrics['accuracy']:.4f} "
            f"val_macro_acc={val_metrics['macro_accuracy']:.4f}"
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

        torch.save(
            {
                "epoch": epoch,
                "class_names": class_names,
                "model_state": model.state_dict(),
                "optimizer_state": optimizer.state_dict(),
                "best_macro_accuracy": best_macro_accuracy,
                "best_val_accuracy": best_val_accuracy,
                "best_state": best_state,
                "patience_counter": patience_counter,
            },
            CHECKPOINT_PATH,
        )

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

    os.makedirs(os.path.dirname(CNN_MODEL_PATH), exist_ok=True)
    torch.save(model.state_dict(), CNN_MODEL_PATH)
    with open(CNN_CLASSES_PATH, "w", encoding="utf-8") as f:
        json.dump(class_names, f, indent=2)
    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)

    report = {
        "classes": class_names,
        "num_images": len(samples),
        "samples_per_class": dict(Counter(class_names[label] for _, label in samples)),
        "val_accuracy": round(final_val.get("accuracy", 0.0), 4),
        "val_macro_accuracy": round(final_val.get("macro_accuracy", 0.0), 4),
        "epochs_frozen": epochs_frozen,
        "epochs_finetune": epochs_finetune,
    }
    with open(CNN_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    result = train_body_scan_cnn()
    print(json.dumps(result, indent=2))
