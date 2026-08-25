from __future__ import annotations

from .training import train_food_scan_model


def main() -> None:
    report = train_food_scan_model()
    print("Food scan model trained successfully")
    print(report)


if __name__ == "__main__":
    main()
