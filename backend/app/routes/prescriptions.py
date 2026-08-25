from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.consultation import ConsultationTicket
from app.models.prescription import Prescription, PrescriptionItem
from app.models.user import User
from app.schemas.prescription import (
    MyPrescriptionResponse,
    PrescriptionCreate,
    PrescriptionItemCreate,
    PrescriptionResponse,
)
from app.services.audit import write_audit_log
from app.services.auth import get_current_user, require_role
from app.services.consultation_ws import manager

router = APIRouter(tags=["Prescriptions"])


def _get_ticket_or_404(db: Session, ticket_id: int) -> ConsultationTicket:
    ticket = db.query(ConsultationTicket).filter(ConsultationTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Consultation not found")
    return ticket


def _ensure_assigned_doctor(ticket: ConsultationTicket, doctor: User) -> None:
    if ticket.doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="Not the assigned doctor for this consultation")


def _add_prescription_items(db: Session, prescription_id: int, items: list[PrescriptionItemCreate]) -> None:
    for item in items:
        db.add(
            PrescriptionItem(
                prescription_id=prescription_id,
                medication_name=item.medication_name,
                dosage=item.dosage,
                frequency=item.frequency,
                duration=item.duration,
                instructions=item.instructions,
            )
        )


def _save_prescription(
    db: Session,
    doctor: User,
    ticket_id: int,
    user_id: int,
    payload: PrescriptionCreate,
    supersedes_id: int | None = None,
) -> Prescription:
    prescription = Prescription(
        ticket_id=ticket_id,
        doctor_id=doctor.id,
        user_id=user_id,
        notes=payload.notes,
        follow_up_date=payload.follow_up_date,
        status="active",
        supersedes_id=supersedes_id,
    )
    db.add(prescription)
    db.flush()

    _add_prescription_items(db, prescription.id, payload.items)

    db.commit()
    db.refresh(prescription)
    return prescription


async def _audit_and_broadcast_prescription(
    db: Session,
    doctor: User,
    prescription: Prescription,
    ticket_id: int,
    event_type: str,
    broadcast_message: str,
    audit_metadata: dict,
) -> None:
    write_audit_log(
        db,
        actor_user_id=doctor.id,
        actor_role=doctor.role,
        event_type=event_type,
        target_type="prescription",
        target_id=str(prescription.id),
        severity="info",
        metadata=audit_metadata,
    )

    await manager.broadcast(
        ticket_id,
        {
            "type": "system",
            "ticket_id": ticket_id,
            "message": broadcast_message,
            "prescription_id": prescription.id,
        },
    )


@router.post(
    "/consultations/{ticket_id}/prescriptions",
    response_model=PrescriptionResponse,
    status_code=201,
)
async def create_prescription(
    ticket_id: int,
    payload: PrescriptionCreate,
    db: Session = Depends(get_db),
    doctor: User = Depends(require_role("doctor")),
):
    ticket = _get_ticket_or_404(db, ticket_id)

    # Ownership before state: a doctor with no relationship to this ticket
    # should get 403 regardless of ticket status, not a 400 that confirms the
    # ticket's status to them.
    _ensure_assigned_doctor(ticket, doctor)

    if ticket.status not in ("accepted", "in_progress"):
        raise HTTPException(status_code=400, detail="Consultation must be active to add a prescription")

    prescription = _save_prescription(db, doctor, ticket.id, ticket.user_id, payload)

    await _audit_and_broadcast_prescription(
        db,
        doctor,
        prescription,
        ticket.id,
        event_type="prescription_created",
        broadcast_message="prescription_added",
        audit_metadata={"ticket_id": ticket.id, "item_count": len(payload.items)},
    )

    return prescription


def _ensure_participant(ticket: ConsultationTicket, user: User) -> None:
    if user.id not in {ticket.user_id, ticket.doctor_id}:
        raise HTTPException(status_code=403, detail="Not allowed to view this consultation's prescriptions")


@router.get(
    "/consultations/{ticket_id}/prescriptions",
    response_model=list[PrescriptionResponse],
)
def list_ticket_prescriptions(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = _get_ticket_or_404(db, ticket_id)
    _ensure_participant(ticket, user)

    return (
        db.query(Prescription)
        .filter(Prescription.ticket_id == ticket.id)
        .order_by(Prescription.created_at.desc())
        .all()
    )


@router.get("/prescriptions/my", response_model=list[MyPrescriptionResponse])
def list_my_prescriptions(
    db: Session = Depends(get_db),
    patient: User = Depends(require_role("user")),
):
    prescriptions = (
        db.query(Prescription)
        .filter(Prescription.user_id == patient.id)
        .order_by(Prescription.created_at.desc())
        .all()
    )

    doctor_ids = {p.doctor_id for p in prescriptions}
    doctor_names = {
        d.id: d.name for d in db.query(User).filter(User.id.in_(doctor_ids)).all()
    }

    return [
        MyPrescriptionResponse(
            **PrescriptionResponse.model_validate(p).model_dump(),
            doctor_name=doctor_names.get(p.doctor_id, "Unknown"),
        )
        for p in prescriptions
    ]


def _get_prescription_or_404(db: Session, prescription_id: int) -> Prescription:
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return prescription


@router.post(
    "/prescriptions/{prescription_id}/supersede",
    response_model=PrescriptionResponse,
    status_code=201,
)
async def supersede_prescription(
    prescription_id: int,
    payload: PrescriptionCreate,
    db: Session = Depends(get_db),
    doctor: User = Depends(require_role("doctor")),
):
    old = _get_prescription_or_404(db, prescription_id)
    if old.doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="Not the doctor who issued this prescription")
    if old.status == "superseded":
        raise HTTPException(status_code=400, detail="This prescription has already been superseded")

    old.status = "superseded"

    new_prescription = _save_prescription(
        db, doctor, old.ticket_id, old.user_id, payload, supersedes_id=old.id
    )

    await _audit_and_broadcast_prescription(
        db,
        doctor,
        new_prescription,
        old.ticket_id,
        event_type="prescription_superseded",
        broadcast_message="prescription_superseded",
        audit_metadata={"ticket_id": old.ticket_id, "supersedes_id": old.id},
    )

    return new_prescription
