from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.sleep import SleepRecord
from app.models.diet import DietRecord
from app.models.health import HealthMetricRecord
from app.models.user import User
from app.services.audit import write_audit_log
from app.services.auth import get_current_user_email
from app.services.escalation import create_consultation_ticket, evaluate_stats_risk
from app.schemas.health import (
    HealthMetricCreate,
    HealthMetricResponse,
    HealthScoreResponse,
)

router = APIRouter(
    prefix="/health",
    tags=["Health"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/score", response_model=HealthScoreResponse)
def get_health_score(
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    last_week = datetime.utcnow() - timedelta(days=7)

    # ---------------- SLEEP SCORE (40) ----------------
    sleep_records = db.query(SleepRecord).filter(
        SleepRecord.user_id == user.id,
        SleepRecord.created_at >= last_week
    ).all()

    sleep_hours = sum(
        (r.sleep_end - r.sleep_start).total_seconds() / 3600
        for r in sleep_records
    )

    avg_sleep = sleep_hours / len(sleep_records) if sleep_records else 0

    sleep_score = min(40, int((avg_sleep / 8) * 40)) if avg_sleep > 0 else 0

    # ---------------- DIET SCORE (40) ----------------
    diet_records = db.query(DietRecord).filter(
        DietRecord.user_id == user.id,
        DietRecord.created_at >= last_week
    ).all()

    avg_calories = (
        sum(r.calories for r in diet_records) / len(diet_records)
        if diet_records else 0
    )

    # No records logged this week is "no data", not "bad intake" — score it
    # 0 like the sleep component does, rather than falling into the same
    # bucket as a genuinely low-calorie week.
    if not diet_records:
        diet_score = 0
    elif avg_calories >= 2000:
        diet_score = 40
    elif avg_calories >= 1500:
        diet_score = 30
    else:
        diet_score = 15

    # ---------------- CONSISTENCY (20) ----------------
    days_tracked = len(set(
        r.created_at.date() for r in sleep_records + diet_records
    ))

    consistency_score = min(20, days_tracked * 3)

    # ---------------- FINAL SCORE ----------------
    total_score = sleep_score + diet_score + consistency_score

    if total_score >= 80:
        status = "Excellent"
        message = "You are maintaining a very healthy lifestyle"
    elif total_score >= 60:
        status = "Good"
        message = "You're doing well, keep improving sleep and diet"
    else:
        status = "Needs Improvement"
        message = "Focus on better sleep and nutrition"

    return {
        "health_score": total_score,
        "status": status,
        "message": message
    }


@router.get("", response_model=list[HealthMetricResponse], status_code=status.HTTP_200_OK)
def get_health_records(
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email),
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    since = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(HealthMetricRecord)
        .filter(
            HealthMetricRecord.user_id == user.id,
            HealthMetricRecord.recorded_at >= since,
        )
        .order_by(HealthMetricRecord.recorded_at.desc())
        .all()
    )


@router.post("/record", response_model=HealthMetricResponse, status_code=status.HTTP_201_CREATED)
def record_health(
    payload: HealthMetricCreate,
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email),
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if (
        payload.steps is None
        and payload.heart_rate is None
        and payload.calories_burned is None
        and payload.systolic_bp is None
        and payload.diastolic_bp is None
        and payload.blood_glucose is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one health metric is required",
        )

    record = HealthMetricRecord(
        user_id=user.id,
        steps=payload.steps,
        heart_rate=payload.heart_rate,
        calories_burned=payload.calories_burned,
        systolic_bp=payload.systolic_bp,
        diastolic_bp=payload.diastolic_bp,
        blood_glucose=payload.blood_glucose,
        recorded_at=payload.recorded_at or datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    heart_rate = payload.heart_rate
    risk = evaluate_stats_risk(
        {
            "heart_rate": heart_rate,
            "systolic_bp": payload.systolic_bp,
            "diastolic_bp": payload.diastolic_bp,
            "blood_glucose": payload.blood_glucose,
        }
    )
    if risk["should_escalate"]:
        ticket = create_consultation_ticket(
            db,
            user=user,
            trigger_source="stats",
            trigger_reason=risk["reason"],
            severity_score=risk["severity_score"],
            category_name=risk["category_name"],
        )
        write_audit_log(
            db,
            actor_user_id=user.id,
            actor_role=user.role,
            event_type="health_escalated",
            target_type="consultation_ticket",
            target_id=str(ticket.id),
            severity=ticket.severity_level,
            metadata={"reason": risk["reason"], "heart_rate": heart_rate},
        )

    return record