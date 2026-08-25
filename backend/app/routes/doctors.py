from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.consultation import ConsultationTicket
from app.models.doctor import DoctorCategory, DoctorProfile
from app.models.prescription import Prescription
from app.models.user import User
from app.schemas.doctor import (
    DoctorCategoryCreate,
    DoctorCategoryResponse,
    DoctorProfileCreate,
    DoctorProfileResponse,
    DoctorReputationResponse,
)
from app.services.auth import get_current_user, require_role

router = APIRouter(prefix="/doctors", tags=["Doctors"])

DEFAULT_DOCTOR_CATEGORY_NAME = "General"


def _avg_response_seconds(db: Session, doctor_user_id: int) -> float | None:
    """Average time between a ticket landing in the queue and this doctor
    accepting it, over all of their accepted tickets. None if they haven't
    accepted any yet."""
    accepted = (
        db.query(ConsultationTicket)
        .filter(
            ConsultationTicket.doctor_id == doctor_user_id,
            ConsultationTicket.accepted_at.isnot(None),
        )
        .all()
    )
    if not accepted:
        return None
    deltas = [(t.accepted_at - t.created_at).total_seconds() for t in accepted]
    return sum(deltas) / len(deltas)


def _active_cases(db: Session, doctor_user_id: int) -> int:
    return (
        db.query(ConsultationTicket)
        .filter(
            ConsultationTicket.doctor_id == doctor_user_id,
            ConsultationTicket.status.in_(["accepted", "in_progress"]),
        )
        .count()
    )


def _prescriptions_issued(db: Session, doctor_user_id: int) -> int:
    return db.query(Prescription).filter(Prescription.doctor_id == doctor_user_id).count()


def _get_or_create_default_category(db: Session) -> DoctorCategory:
    category = (
        db.query(DoctorCategory)
        .filter(DoctorCategory.name == DEFAULT_DOCTOR_CATEGORY_NAME)
        .first()
    )
    if category:
        return category

    category = DoctorCategory(
        name=DEFAULT_DOCTOR_CATEGORY_NAME,
        description="Auto-created default category",
    )
    db.add(category)
    db.flush()
    return category


@router.get("/categories", response_model=list[DoctorCategoryResponse])
def list_doctor_categories(db: Session = Depends(get_db)):
    return db.query(DoctorCategory).order_by(DoctorCategory.name.asc()).all()


@router.post(
    "/categories",
    response_model=DoctorCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_doctor_category(
    payload: DoctorCategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("doctor")),
):
    exists = db.query(DoctorCategory).filter(DoctorCategory.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Category already exists")

    category = DoctorCategory(name=payload.name, description=payload.description)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.post(
    "/profile",
    response_model=DoctorProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_doctor_profile(
    payload: DoctorProfileCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("doctor")),
):
    category = db.query(DoctorCategory).filter(DoctorCategory.id == payload.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Doctor category not found")

    existing_profile = (
        db.query(DoctorProfile).filter(DoctorProfile.user_id == user.id).first()
    )
    if existing_profile:
        raise HTTPException(status_code=400, detail="Doctor profile already exists")

    duplicate_license = (
        db.query(DoctorProfile)
        .filter(DoctorProfile.license_number == payload.license_number)
        .first()
    )
    if duplicate_license:
        raise HTTPException(status_code=400, detail="License number already in use")

    profile = DoctorProfile(
        user_id=user.id,
        category_id=payload.category_id,
        license_number=payload.license_number,
        years_experience=payload.years_experience,
        bio=payload.bio,
        is_available=payload.is_available,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return DoctorProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        doctor_name=user.name,
        category_id=profile.category_id,
        category_name=category.name,
        license_number=profile.license_number,
        years_experience=profile.years_experience,
        bio=profile.bio,
        is_available=profile.is_available,
        average_rating=profile.average_rating,
        total_ratings=profile.total_ratings,
        total_consultations=profile.total_consultations,
        created_at=profile.created_at,
    )


@router.get("/me/profile", response_model=DoctorProfileResponse)
def get_my_doctor_profile(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("doctor")),
):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user.id).first()
    if not profile:
        category = _get_or_create_default_category(db)
        profile = DoctorProfile(
            user_id=user.id,
            category_id=category.id,
            license_number=f"AUTO-{user.id}",
            years_experience=0,
            bio="Auto-generated doctor profile",
            is_available=True,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    category = db.query(DoctorCategory).filter(DoctorCategory.id == profile.category_id).first()
    category_name = category.name if category else "Unknown"

    return DoctorProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        doctor_name=user.name,
        category_id=profile.category_id,
        category_name=category_name,
        license_number=profile.license_number,
        years_experience=profile.years_experience,
        bio=profile.bio,
        is_available=profile.is_available,
        average_rating=profile.average_rating,
        total_ratings=profile.total_ratings,
        total_consultations=profile.total_consultations,
        created_at=profile.created_at,
        avg_response_seconds=_avg_response_seconds(db, user.id),
        active_cases=_active_cases(db, user.id),
        prescriptions_issued=_prescriptions_issued(db, user.id),
    )


@router.patch("/me/availability", response_model=dict)
def update_doctor_availability(
    is_available: bool,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("doctor")),
):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    profile.is_available = is_available
    db.commit()
    return {"doctor_id": user.id, "is_available": profile.is_available}


@router.get("/available", response_model=list[DoctorProfileResponse])
def list_available_doctors(
    category_name: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(DoctorProfile).filter(DoctorProfile.is_available.is_(True))

    category = None
    if category_name:
        category = (
            db.query(DoctorCategory).filter(DoctorCategory.name == category_name).first()
        )
        if not category:
            return []
        query = query.filter(DoctorProfile.category_id == category.id)

    profiles = (
        query.order_by(
            DoctorProfile.average_rating.desc(),
            DoctorProfile.total_consultations.desc(),
        )
        # A hard cap, not real pagination — this app has nowhere near enough
        # doctors for that to matter yet, but an unbounded .all() here would
        # load and serialize the whole table on every call.
        .limit(200)
        .all()
    )

    categories_by_id = {
        c.id: c.name for c in db.query(DoctorCategory).filter(DoctorCategory.id.in_([p.category_id for p in profiles])).all()
    }
    names_by_user_id = {
        u.id: u.name for u in db.query(User).filter(User.id.in_([p.user_id for p in profiles])).all()
    }

    return [
        DoctorProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            doctor_name=names_by_user_id.get(profile.user_id, "Unknown"),
            category_id=profile.category_id,
            category_name=categories_by_id.get(profile.category_id, "Unknown"),
            license_number=profile.license_number,
            years_experience=profile.years_experience,
            bio=profile.bio,
            is_available=profile.is_available,
            average_rating=profile.average_rating,
            total_ratings=profile.total_ratings,
            total_consultations=profile.total_consultations,
            created_at=profile.created_at,
        )
        for profile in profiles
    ]


@router.get("/{doctor_id}/reputation", response_model=DoctorReputationResponse)
def get_doctor_reputation(
    doctor_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    doctor_user = db.query(User).filter(User.id == doctor_id, User.role == "doctor").first()
    if not doctor_user:
        raise HTTPException(status_code=404, detail="Doctor not found")

    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == doctor_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    category = db.query(DoctorCategory).filter(DoctorCategory.id == profile.category_id).first()

    return DoctorReputationResponse(
        doctor_id=doctor_id,
        average_rating=profile.average_rating,
        total_ratings=profile.total_ratings,
        total_consultations=profile.total_consultations,
        category_name=category.name if category else "Unknown",
    )
