import uuid

import app.main  # noqa: F401 - Ensure Base.metadata.create_all is called
from app.database import SessionLocal
from app.models.doctor import DoctorCategory, DoctorProfile
from app.models.user import User
from app.services.escalation import _assign_best_doctor


def _make_doctor(db, *, category_id: int, rating: float, consultations: int) -> User:
    email = f"doctor-assignment-{uuid.uuid4().hex[:10]}@example.com"
    user = User(name="Doctor User", email=email, password="hashed", role="doctor")
    db.add(user)
    db.flush()

    profile = DoctorProfile(
        user_id=user.id,
        category_id=category_id,
        license_number=f"LIC-{uuid.uuid4().hex[:10]}",
        is_available=True,
        average_rating=rating,
        total_consultations=consultations,
    )
    db.add(profile)
    db.flush()
    return user


def _make_category(db, name_prefix: str) -> DoctorCategory:
    category = DoctorCategory(name=f"{name_prefix}-{uuid.uuid4().hex[:10]}")
    db.add(category)
    db.flush()
    return category


def test_picks_highest_rated_doctor_within_matching_category():
    db = SessionLocal()
    try:
        category = _make_category(db, "Cardiology")
        low = _make_doctor(db, category_id=category.id, rating=3.0, consultations=50)
        high = _make_doctor(db, category_id=category.id, rating=4.8, consultations=1)
        db.commit()

        chosen = _assign_best_doctor(db, category.name)
        assert chosen is not None
        assert chosen.id == high.id
        assert chosen.id != low.id
    finally:
        db.close()


def test_equal_rating_no_longer_tie_broken_by_total_consultations():
    db = SessionLocal()
    try:
        category = _make_category(db, "Cardiology")
        created_first = _make_doctor(db, category_id=category.id, rating=4.0, consultations=1)
        created_second_more_consultations = _make_doctor(db, category_id=category.id, rating=4.0, consultations=200)
        db.commit()

        chosen = _assign_best_doctor(db, category.name)
        assert chosen is not None
        # Same rating: total_consultations must NOT be used as a tie-break anymore.
        # Deterministic tie-break is doctor id (creation order), not consultation count.
        assert chosen.id == created_first.id
        assert chosen.id != created_second_more_consultations.id
    finally:
        db.close()


def test_unknown_category_falls_back_to_highest_rated_available_doctor():
    db = SessionLocal()
    try:
        category = _make_category(db, "Nutrition")
        low = _make_doctor(db, category_id=category.id, rating=2.0, consultations=10)
        high = _make_doctor(db, category_id=category.id, rating=4.9, consultations=10)
        db.commit()

        chosen = _assign_best_doctor(db, "Not A Real Category")
        assert chosen is not None
        assert chosen.id == high.id
    finally:
        db.close()


def test_category_with_no_available_doctors_returns_none_not_a_fallback():
    db = SessionLocal()
    try:
        empty_category = _make_category(db, "Dermatology")
        other_category = _make_category(db, "Nutrition")
        _make_doctor(db, category_id=other_category.id, rating=5.0, consultations=10)
        db.commit()

        chosen = _assign_best_doctor(db, empty_category.name)
        assert chosen is None
    finally:
        db.close()
