from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.sleep import SleepRecord
from app.models.diet import DietRecord
from app.models.user import User


def get_health_context(db: Session, user_email: str) -> dict:
    """
    Collects recent health data for chatbot context
    """

    # -------- Safety check for testing --------
    if db is None:
        return {
            "avg_sleep_hours": 7,
            "avg_calories": 2200,
            "sleep_days_tracked": 0,
            "diet_days_tracked": 0,
        }

    # -------- Get user --------
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return {}

    last_week = datetime.utcnow() - timedelta(days=7)

    # -------- Sleep --------
    sleep_records = db.query(SleepRecord).filter(
        SleepRecord.user_id == user.id,
        SleepRecord.created_at >= last_week
    ).all()

    sleep_hours = [
        (r.sleep_end - r.sleep_start).total_seconds() / 3600
        for r in sleep_records
    ]

    avg_sleep = round(sum(sleep_hours) / len(sleep_hours), 2) if sleep_hours else 0

    # -------- Diet --------
    diet_records = db.query(DietRecord).filter(
        DietRecord.user_id == user.id,
        DietRecord.created_at >= last_week
    ).all()

    calories = [d.calories for d in diet_records]
    avg_calories = round(sum(calories) / len(calories), 2) if calories else 0

    return {
        "avg_sleep_hours": avg_sleep,
        "avg_calories": avg_calories,
        "sleep_days_tracked": len(sleep_records),
        "diet_days_tracked": len(diet_records),
    }