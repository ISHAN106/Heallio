from datetime import date

import app.main  # noqa: F401 - Ensure Base.metadata.create_all is called
from app.database import SessionLocal
from app.models.consultation import ConsultationTicket
from app.models.prescription import Prescription, PrescriptionItem
from app.models.user import User


def _make_user(db, email: str, role: str) -> User:
    user = User(name=f"{role.title()} User", email=email, password="hashed", role=role)
    db.add(user)
    db.flush()
    return user


def test_prescription_with_items_persists_and_cascades():
    db = SessionLocal()
    try:
        patient = _make_user(db, "prescription-model-patient@example.com", "user")
        doctor = _make_user(db, "prescription-model-doctor@example.com", "doctor")
        ticket = ConsultationTicket(
            user_id=patient.id,
            doctor_id=doctor.id,
            trigger_source="manual",
            trigger_reason="test",
            severity_score=50,
            severity_level="medium",
            status="in_progress",
        )
        db.add(ticket)
        db.flush()

        prescription = Prescription(
            ticket_id=ticket.id,
            doctor_id=doctor.id,
            user_id=patient.id,
            notes="Rest and hydrate",
            follow_up_date=date(2026, 7, 20),
            status="active",
        )
        db.add(prescription)
        db.flush()

        item = PrescriptionItem(
            prescription_id=prescription.id,
            medication_name="Paracetamol",
            dosage="500mg",
            frequency="twice daily",
            duration="3 days",
        )
        db.add(item)
        db.commit()

        db.refresh(prescription)
        assert len(prescription.items) == 1
        assert prescription.items[0].medication_name == "Paracetamol"

        prescription_id = prescription.id
        db.delete(prescription)
        db.commit()

        assert db.query(PrescriptionItem).filter(PrescriptionItem.prescription_id == prescription_id).first() is None
    finally:
        db.query(User).filter(
            User.email.in_(["prescription-model-patient@example.com", "prescription-model-doctor@example.com"])
        ).delete(synchronize_session=False)
        db.commit()
        db.close()
