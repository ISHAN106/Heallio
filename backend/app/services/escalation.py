from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.consultation import ConsultationTicket
from app.models.doctor import DoctorCategory, DoctorProfile
from app.models.user import User
from ml.chatbot.health_context import get_health_context

RISK_KEYWORDS = {
    "critical": [
        "suicide",
        "kill myself",
        "chest pain",
        "faint",
        "unconscious",
        "overdose",
        "stroke",
    ],
    "high": [
        "panic attack",
        "severe pain",
        "heart racing",
        "can't breathe",
        "breathing problem",
        "blood pressure very high",
    ],
    "medium": [
        "depressed",
        "anxiety",
        "dizzy",
        "very tired",
        "insomnia",
    ],
}

SELF_HARM_PHRASES = [
    "hurt myself",
    "end my life",
    "suicidal",
    "don't want to live",
    "kill myself",
]

ACUTE_PHRASES = [
    "chest pain",
    "can't breathe",
    "difficulty breathing",
    "passing out",
    "fainting",
    "seizure",
]


def _severity_from_score(score: int) -> str:
    if score >= 90:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def _best_category_for_context(message: str, context: dict) -> str:
    msg = message.lower()
    if any(token in msg for token in ["anxiety", "depress", "panic", "stress"]):
        return "Mental Health"
    if any(token in msg for token in ["heart", "chest", "palpitation", "pressure"]):
        return "Cardiology"

    avg_calories = context.get("avg_calories", 0)
    if avg_calories and (avg_calories < 1200 or avg_calories > 3400):
        return "Nutrition"

    return "General Physician"


def _assign_best_doctor(db: Session, category_name: str | None) -> User | None:
    query = (
        db.query(DoctorProfile)
        .join(User, DoctorProfile.user_id == User.id)
        .filter(User.role == "doctor", DoctorProfile.is_available.is_(True))
    )

    if category_name:
        category = (
            db.query(DoctorCategory).filter(DoctorCategory.name == category_name).first()
        )
        if category:
            query = query.filter(DoctorProfile.category_id == category.id)
        # else: category_name didn't match a known category (e.g. misspelled) --
        # fall back to the highest-rated doctor across all available doctors
        # rather than returning no match.

    doctor_profile = (
        query.order_by(DoctorProfile.average_rating.desc(), DoctorProfile.id.asc())
        .first()
    )

    if doctor_profile:
        return db.query(User).filter(User.id == doctor_profile.user_id).first()

    return None


def find_recent_open_ticket(db: Session, user_id: int) -> ConsultationTicket | None:
    window_start = datetime.utcnow() - timedelta(hours=6)
    return (
        db.query(ConsultationTicket)
        .filter(
            ConsultationTicket.user_id == user_id,
            ConsultationTicket.status.in_(["pending", "accepted", "in_progress"]),
            ConsultationTicket.created_at >= window_start,
        )
        .order_by(ConsultationTicket.created_at.desc())
        .first()
    )


def create_consultation_ticket(
    db: Session,
    *,
    user: User,
    trigger_source: str,
    trigger_reason: str,
    severity_score: int,
    category_name: str,
) -> ConsultationTicket:
    existing = find_recent_open_ticket(db, user.id)
    if existing:
        # A new, more severe signal should upgrade the existing open ticket
        # rather than being silently dropped — otherwise a critical signal
        # (e.g. a self-harm phrase in chat) never surfaces if a lower-severity
        # ticket is already open from earlier in the 6-hour window.
        if severity_score > existing.severity_score:
            existing.severity_score = severity_score
            existing.severity_level = _severity_from_score(severity_score)
            existing.trigger_source = trigger_source
            existing.trigger_reason = trigger_reason
            db.commit()
            db.refresh(existing)
        return existing

    doctor = _assign_best_doctor(db, category_name)
    ticket = ConsultationTicket(
        user_id=user.id,
        doctor_id=doctor.id if doctor else None,
        trigger_source=trigger_source,
        trigger_reason=trigger_reason,
        severity_score=severity_score,
        severity_level=_severity_from_score(severity_score),
        status="accepted" if doctor else "pending",
        accepted_at=datetime.utcnow() if doctor else None,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def evaluate_chat_risk(
    db: Session, user: User, message: str, context: dict | None = None
) -> dict:
    text = message.lower().strip()
    if context is None:
        context = get_health_context(db, user.email)

    score = 0
    if any(token in text for token in SELF_HARM_PHRASES):
        score = 100
    elif any(token in text for token in ACUTE_PHRASES):
        score = 95

    for weight, level in [(50, "medium"), (75, "high"), (95, "critical")]:
        if any(token in text for token in RISK_KEYWORDS[level]):
            score = max(score, weight)

    avg_sleep = context.get("avg_sleep_hours", 0)
    avg_calories = context.get("avg_calories", 0)

    if avg_sleep and avg_sleep < 4:
        score = max(score, 70)
    elif avg_sleep and avg_sleep < 5.5:
        score = max(score, 55)

    if context.get("sleep_days_tracked", 0) == 0 or context.get("diet_days_tracked", 0) == 0:
        score = max(score, 45)

    if avg_calories and (avg_calories < 1000 or avg_calories > 3800):
        score = max(score, 70)
    elif avg_calories and (avg_calories < 1300 or avg_calories > 3300):
        score = max(score, 50)

    if any(token in text for token in ["vomit", "dehydrated", "blackout", "confused"]):
        score = max(score, 80)

    severity = _severity_from_score(score)
    should_escalate = severity in {"high", "critical"}
    category_name = _best_category_for_context(message, context)

    return {
        "should_escalate": should_escalate,
        "severity_score": score,
        "severity_level": severity,
        "category_name": category_name,
        "reason": "Risk detected from chatbot conversation and recent health context.",
        "context": context,
    }


def evaluate_stats_risk(payload: dict) -> dict:
    score = 0
    reasons = []

    calories = payload.get("calories")
    if calories is not None:
        if calories < 800 or calories > 4500:
            score = max(score, 85)
            reasons.append("Unusually extreme calorie intake detected")
        elif calories < 1200 or calories > 3200:
            score = max(score, 65)
            reasons.append("Potentially risky calorie trend detected")

    heart_rate = payload.get("heart_rate")
    if heart_rate is not None:
        if heart_rate < 38 or heart_rate > 145:
            score = max(score, 90)
            reasons.append("Potentially dangerous heart rate detected")
        elif heart_rate < 50 or heart_rate > 115:
            score = max(score, 70)
            reasons.append("Abnormal heart rate trend detected")

    steps = payload.get("steps")
    if steps is not None and steps < 1000:
        score = max(score, 45)
        reasons.append("Very low activity reported")

    systolic_bp = payload.get("systolic_bp")
    diastolic_bp = payload.get("diastolic_bp")
    bp_flagged = False
    if systolic_bp is not None or diastolic_bp is not None:
        if (systolic_bp is not None and (systolic_bp >= 180 or systolic_bp < 70)) or (
            diastolic_bp is not None and (diastolic_bp >= 120 or diastolic_bp < 40)
        ):
            score = max(score, 90)
            reasons.append("Potentially dangerous blood pressure detected")
            bp_flagged = True
        elif (systolic_bp is not None and (systolic_bp >= 140 or systolic_bp < 90)) or (
            diastolic_bp is not None and (diastolic_bp >= 90 or diastolic_bp < 60)
        ):
            score = max(score, 70)
            reasons.append("Abnormal blood pressure trend detected")
            bp_flagged = True

    blood_glucose = payload.get("blood_glucose")
    if blood_glucose is not None:
        if blood_glucose < 54 or blood_glucose > 400:
            score = max(score, 90)
            reasons.append("Potentially dangerous blood glucose detected")
        elif blood_glucose < 70 or blood_glucose > 250:
            score = max(score, 70)
            reasons.append("Abnormal blood glucose trend detected")

    severity = _severity_from_score(score)
    should_escalate = severity in {"high", "critical"}

    if heart_rate is not None or bp_flagged:
        category = "Cardiology"
    elif blood_glucose is not None or calories is not None:
        category = "Nutrition"
    else:
        category = "General Physician"

    return {
        "should_escalate": should_escalate,
        "severity_score": score,
        "severity_level": severity,
        "category_name": category,
        "reason": "; ".join(reasons) if reasons else "No critical pattern detected",
    }
