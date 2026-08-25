from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.schemas.sleep import SleepCreate
from app.models.sleep import SleepRecord
from app.models.user import User
from app.services.auth import get_current_user_email
from datetime import datetime, timedelta
from app.schemas.sleep import SleepCreate, SleepSummaryResponse


router = APIRouter(
    prefix="/sleep",
    tags=["Sleep"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/log")
def log_sleep(
    data: SleepCreate,   # ✅ THIS MAKES IT JSON BODY
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if data.sleep_end <= data.sleep_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sleep_end must be after sleep_start",
        )

    record = SleepRecord(
        sleep_start=data.sleep_start,
        sleep_end=data.sleep_end,
        quality=data.quality,
        user_id=user.id
    )

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/my-records")
def get_my_sleep_records(
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    records = (
        db.query(SleepRecord)
        .filter(SleepRecord.user_id == user.id)
        .order_by(SleepRecord.created_at.desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "user_id": user.id,
            "sleep_start": r.sleep_start,
            "sleep_end": r.sleep_end,
            "quality": r.quality,
            "recorded_at": r.created_at,
        }
        for r in records
    ]

@router.get("/summary", response_model=SleepSummaryResponse)
def sleep_summary(
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Scoped to the last 7 days to match /health/score and /insights/weekly —
    # previously this was a lifetime average, which could contradict those
    # endpoints for the same user at the same time.
    last_week = datetime.utcnow() - timedelta(days=7)
    records = db.query(SleepRecord).filter(
        SleepRecord.user_id == user.id,
        SleepRecord.created_at >= last_week,
    ).all()

    total_hours = 0
    quality_count = {"good": 0, "average": 0, "poor": 0}

    for r in records:
        duration = (r.sleep_end - r.sleep_start).total_seconds() / 3600
        total_hours += duration
        if r.quality in quality_count:
            quality_count[r.quality] += 1

    avg_sleep = round(total_hours / len(records), 2) if records else 0

    return {
        "days_tracked": len(records),
        "total_sleep_hours": round(total_hours, 2),
        "average_sleep_hours": avg_sleep,
        "sleep_quality_breakdown": quality_count
    }
    
