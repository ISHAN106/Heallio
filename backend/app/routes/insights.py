from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.sleep import SleepRecord
from app.models.diet import DietRecord
from app.models.user import User
from app.services.auth import get_current_user_email
from app.schemas.insights import WeeklyInsightsResponse

router = APIRouter(
    prefix="/insights",
    tags=["Insights"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/weekly", response_model=WeeklyInsightsResponse)
def weekly_insights(
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email)
):
    # -------- USER --------
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    last_week = datetime.utcnow() - timedelta(days=7)

    # -------- SLEEP --------
    sleep_records = db.query(SleepRecord).filter(
        SleepRecord.user_id == user.id,
        SleepRecord.created_at >= last_week
    ).all()

    sleep_hours = [
        (r.sleep_end - r.sleep_start).total_seconds() / 3600
        for r in sleep_records
    ]

    avg_sleep = sum(sleep_hours) / len(sleep_hours) if sleep_hours else 0
    variation = max(sleep_hours) - min(sleep_hours) if sleep_hours else 0

    if avg_sleep < 6:
        sleep_message = "You have a sleep deficit. Chronic low sleep affects focus and immunity."
        sleep_status = "poor"
        sleep_score = 15
    elif avg_sleep < 7:
        sleep_message = "Your sleep is slightly below ideal. Improve consistency."
        sleep_status = "average"
        sleep_score = 25
    elif avg_sleep <= 8:
        sleep_message = "Your sleep duration is ideal."
        sleep_status = "good"
        sleep_score = 40
    else:
        sleep_message = "You may be oversleeping. Quality matters more than quantity."
        sleep_status = "average"
        sleep_score = 30

    if variation > 2:
        sleep_message += " Your sleep timing is inconsistent."
        sleep_score -= 10

    # -------- DIET --------
    diet_records = db.query(DietRecord).filter(
        DietRecord.user_id == user.id,
        DietRecord.created_at >= last_week
    ).all()

    calories = [d.calories for d in diet_records if d.calories is not None]
    avg_calories = sum(calories) / len(calories) if calories else 0

    if avg_calories > 2700:
        diet_message = "High calorie intake detected. Consider portion control."
        diet_status = "poor"
        diet_score = 25
    elif avg_calories < 1800:
        diet_message = "Low calorie intake detected. Ensure proper nutrition."
        diet_status = "poor"
        diet_score = 25
    else:
        diet_message = "Your calorie intake appears balanced."
        diet_status = "good"
        diet_score = 40

    # -------- OVERALL --------
    total_score = sleep_score + diet_score

    if total_score >= 80:
        overall_tip = "Excellent lifestyle balance. Keep maintaining these habits."
    elif total_score >= 60:
        overall_tip = "Good overall health. Small improvements will make a big difference."
    else:
        overall_tip = "Your routine needs attention. Focus on sleep regularity and nutrition."

    return {
        "sleep": {
            "status": sleep_status,
            "message": sleep_message
        },
        "diet": {
            "status": diet_status,
            "message": diet_message
        },
        "consistency": {
            "status": "good",
            "message": "You are consistently logging your health data."
        },
        "overall_suggestion": overall_tip
    }