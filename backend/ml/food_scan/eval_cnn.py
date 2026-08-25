from __future__ import annotations

import json
from collections import defaultdict

import torch
from torch.utils.data import DataLoader, Subset

from .cnn import CNN_CLASSES_PATH, CNN_MODEL_PATH, FoodCNN, build_inference_transform
from .train_cnn import DEVICE, FoodImageDataset, _discover_samples, _stratified_split

BASE_DIR_REPORT = CNN_CLASSES_PATH.replace("food_scan_cnn_classes.json", "food_scan_cnn_per_class_report.json")


def main() -> None:
    with open(CNN_CLASSES_PATH, "r", encoding="utf-8") as f:
        class_names = json.load(f)

    samples, portions, discovered_classes = _discover_samples()
    assert discovered_classes == class_names, "class order mismatch between dataset and saved classes.json"
    _, val_idx = _stratified_split(samples)

    eval_dataset = FoodImageDataset(samples, portions, build_inference_transform())
    val_loader = DataLoader(Subset(eval_dataset, val_idx), batch_size=32, shuffle=False, num_workers=0)

    model = FoodCNN(num_classes=len(class_names)).to(DEVICE)
    state = torch.load(CNN_MODEL_PATH, map_location=DEVICE)
    model.load_state_dict(state)
    model.eval()

    correct_per_class: dict[int, int] = defaultdict(int)
    total_per_class: dict[int, int] = defaultdict(int)
    confused_as: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))

    with torch.no_grad():
        for images, labels, _ in val_loader:
            images = images.to(DEVICE)
            labels = labels.to(DEVICE)
            logits, _ = model(images)
            preds = logits.argmax(dim=1)
            for label, pred in zip(labels.tolist(), preds.tolist()):
                total_per_class[label] += 1
                if pred == label:
                    correct_per_class[label] += 1
                else:
                    confused_as[label][pred] += 1

    rows = []
    for idx, name in enumerate(class_names):
        total = total_per_class.get(idx, 0)
        correct = correct_per_class.get(idx, 0)
        acc = (correct / total) if total else None
        top_confusion = None
        if confused_as[idx]:
            worst_idx, worst_count = max(confused_as[idx].items(), key=lambda kv: kv[1])
            top_confusion = {"predicted_as": class_names[worst_idx], "count": worst_count}
        rows.append(
            {
                "class": name,
                "val_samples": total,
                "correct": correct,
                "accuracy": round(acc, 4) if acc is not None else None,
                "top_confusion": top_confusion,
            }
        )

    rows.sort(key=lambda r: (r["accuracy"] is None, r["accuracy"] if r["accuracy"] is not None else 0))

    overall_correct = sum(correct_per_class.values())
    overall_total = sum(total_per_class.values())
    report = {
        "overall_val_accuracy": round(overall_correct / overall_total, 4) if overall_total else None,
        "num_val_samples": overall_total,
        "classes_with_zero_val_samples": [r["class"] for r in rows if r["val_samples"] == 0],
        "per_class": rows,
    }

    with open(BASE_DIR_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Overall val accuracy: {report['overall_val_accuracy']} ({overall_total} val samples)")
    print(f"Classes with 0 val samples: {len(report['classes_with_zero_val_samples'])}")
    print("\nWorst 20 classes:")
    for r in rows[:20]:
        conf = r["top_confusion"]
        conf_str = f" -> confused with {conf['predicted_as']} ({conf['count']}x)" if conf else ""
        print(f"  {r['class']:35s} acc={r['accuracy']} n={r['val_samples']}{conf_str}")
    print("\nBest 10 classes:")
    for r in rows[-10:]:
        print(f"  {r['class']:35s} acc={r['accuracy']} n={r['val_samples']}")
    print(f"\nFull report written to {BASE_DIR_REPORT}")


if __name__ == "__main__":
    main()
