from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.diet import DietRecord
from app.models.user import User
from app.schemas.diet import DietCreate, DietResponse
from app.services.audit import write_audit_log
from app.services.auth import get_current_user_email
from app.services.escalation import create_consultation_ticket, evaluate_stats_risk

router = APIRouter(
    prefix="/diet",
    tags=["Diet"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------
# LOG DIET
# -------------------------
@router.post("/log", response_model=DietResponse)
def log_diet(
    data: DietCreate,
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    record = DietRecord(
        user_id=user.id,
        meal_type=data.meal_type,
        food=data.food,
        calories=data.calories,
        notes=data.notes
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    risk = evaluate_stats_risk({"calories": data.calories})
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
            event_type="diet_escalated",
            target_type="consultation_ticket",
            target_id=str(ticket.id),
            severity=ticket.severity_level,
            metadata={"reason": risk["reason"], "calories": data.calories},
        )

    return record

# -------------------------
# VIEW MY DIET LOGS
# -------------------------
@router.get("/my-records", response_model=list[DietResponse])
def get_my_diet_records(
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return (
        db.query(DietRecord)
        .filter(DietRecord.user_id == user.id)
        .order_by(DietRecord.created_at.desc())
        .all()
    )