from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models.consultation import ConsultationMessage, ConsultationTicket, DoctorRating
from app.models.doctor import DoctorProfile
from app.models.user import User
from app.schemas.consultation import (
    ConsultationCreateManual,
    ConsultationMessageCreate,
    ConsultationMessageResponse,
    ConsultationTicketResponse,
    DoctorRatingCreate,
)
from app.services.audit import write_audit_log
from app.services.auth import (
    get_current_user,
    is_session_revoked,
    require_role,
    token_issued_before_revocation,
)
from app.services.consultation_ws import manager
from app.services.escalation import create_consultation_ticket
from app.services.jwt import decode_token

router = APIRouter(prefix="/consultations", tags=["Consultations"])


def _get_ticket_or_404(db: Session, ticket_id: int) -> ConsultationTicket:
    ticket = db.query(ConsultationTicket).filter(ConsultationTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Consultation not found")
    return ticket


def _ensure_access(ticket: ConsultationTicket, user: User) -> None:
    if user.id not in {ticket.user_id, ticket.doctor_id}:
        raise HTTPException(status_code=403, detail="Not allowed in this consultation")


@router.post("/manual", response_model=ConsultationTicketResponse)
def create_manual_consultation(
    payload: ConsultationCreateManual,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("user")),
):
    ticket = create_consultation_ticket(
        db,
        user=user,
        trigger_source="manual",
        trigger_reason=payload.reason,
        severity_score=65,
        category_name=payload.category_name or "General Physician",
    )
    write_audit_log(
        db,
        actor_user_id=user.id,
        actor_role=user.role,
        event_type="consultation_created",
        target_type="consultation_ticket",
        target_id=str(ticket.id),
        severity=ticket.severity_level,
        metadata={
            "trigger_source": ticket.trigger_source,
            "severity_score": ticket.severity_score,
            "category": payload.category_name or "General Physician",
        },
    )
    return ticket


@router.get("/my", response_model=list[ConsultationTicketResponse])
def get_my_consultations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == "doctor":
        return (
            db.query(ConsultationTicket)
            .filter(ConsultationTicket.doctor_id == user.id)
            .order_by(ConsultationTicket.created_at.desc())
            .all()
        )

    return (
        db.query(ConsultationTicket)
        .filter(ConsultationTicket.user_id == user.id)
        .order_by(ConsultationTicket.created_at.desc())
        .all()
    )


@router.get("/queue", response_model=list[ConsultationTicketResponse])
def get_consultation_queue(
    db: Session = Depends(get_db),
    doctor: User = Depends(require_role("doctor")),
):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == doctor.id).first()
    if profile and not profile.is_available:
        return []

    return (
        db.query(ConsultationTicket)
        .filter(ConsultationTicket.status == "pending")
        .order_by(ConsultationTicket.created_at.asc())
        .all()
    )


@router.post("/{ticket_id}/accept", response_model=ConsultationTicketResponse)
def accept_consultation(
    ticket_id: int,
    db: Session = Depends(get_db),
    doctor: User = Depends(require_role("doctor")),
):
    # Row lock so two doctors racing to accept the same pending ticket can't
    # both read doctor_id as unset and both win — the second request blocks
    # here until the first commits, then re-reads the now-assigned ticket.
    ticket = (
        db.query(ConsultationTicket)
        .filter(ConsultationTicket.id == ticket_id)
        .with_for_update()
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Consultation not found")

    if ticket.doctor_id and ticket.doctor_id != doctor.id:
        raise HTTPException(status_code=409, detail="Consultation already assigned")

    if ticket.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Consultation is '{ticket.status}', not pending — cannot accept",
        )

    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == doctor.id).first()
    if profile and not profile.is_available:
        raise HTTPException(status_code=400, detail="Doctor is unavailable")

    ticket.doctor_id = doctor.id
    ticket.status = "accepted"
    ticket.accepted_at = datetime.utcnow()

    db.commit()
    db.refresh(ticket)

    write_audit_log(
        db,
        actor_user_id=doctor.id,
        actor_role=doctor.role,
        event_type="consultation_accepted",
        target_type="consultation_ticket",
        target_id=str(ticket.id),
        severity=ticket.severity_level,
        metadata={"doctor_id": doctor.id},
    )
    return ticket


@router.post("/{ticket_id}/messages", response_model=ConsultationMessageResponse)
def send_consultation_message(
    ticket_id: int,
    payload: ConsultationMessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = _get_ticket_or_404(db, ticket_id)
    _ensure_access(ticket, user)

    if ticket.status == "closed":
        raise HTTPException(status_code=400, detail="Consultation is already closed")

    if ticket.status == "accepted":
        ticket.status = "in_progress"

    message = ConsultationMessage(
        ticket_id=ticket.id,
        sender_user_id=user.id,
        message=payload.message,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    write_audit_log(
        db,
        actor_user_id=user.id,
        actor_role=user.role,
        event_type="consultation_message_sent",
        target_type="consultation_ticket",
        target_id=str(ticket.id),
        severity=ticket.severity_level,
        metadata={"message_length": len(payload.message)},
    )

    return message


@router.websocket("/ws/{ticket_id}")
async def consultation_websocket(websocket: WebSocket, ticket_id: int):
    db = SessionLocal()
    try:
        # Token arrives via the Sec-WebSocket-Protocol header ("bearer, <jwt>")
        # instead of a query param, so it stays out of server/proxy access logs.
        protocols = [
            p.strip()
            for p in websocket.headers.get("sec-websocket-protocol", "").split(",")
            if p.strip()
        ]
        token = protocols[1] if len(protocols) >= 2 and protocols[0] == "bearer" else None
        if not token:
            await websocket.close(code=4401)
            return
        try:
            payload = decode_token(token)
        except Exception:
            await websocket.close(code=4401)
            return
        if payload.get("token_type") == "refresh":
            await websocket.close(code=4401)
            return
        email = payload.get("sub")
        if not email:
            await websocket.close(code=4401)
            return

        user = db.query(User).filter(User.email == email).first()
        if not user:
            await websocket.close(code=4404)
            return

        if token_issued_before_revocation(payload, user):
            await websocket.close(code=4401)
            return

        if is_session_revoked(db, payload.get("sid")):
            await websocket.close(code=4401)
            return

        ticket = db.query(ConsultationTicket).filter(ConsultationTicket.id == ticket_id).first()
        if not ticket:
            await websocket.close(code=4404)
            return

        if user.id not in {ticket.user_id, ticket.doctor_id}:
            await websocket.close(code=4403)
            return

        await manager.connect(ticket_id, websocket, subprotocol="bearer")
        await manager.broadcast(
            ticket_id,
            {
                "type": "system",
                "ticket_id": ticket_id,
                "message": "connected",
                "user_id": user.id,
            },
        )

        while True:
            incoming = await websocket.receive_json()
            message_text = (incoming.get("message") or "").strip()
            if not message_text:
                continue

            # Refresh before checking status — the ticket could have been
            # closed via the REST endpoint by the other participant while
            # this socket stayed open.
            db.refresh(ticket)
            if ticket.status == "closed":
                await websocket.send_json(
                    {
                        "type": "error",
                        "ticket_id": ticket.id,
                        "message": "This consultation is closed.",
                    }
                )
                continue

            if ticket.status == "accepted":
                ticket.status = "in_progress"

            message = ConsultationMessage(
                ticket_id=ticket.id,
                sender_user_id=user.id,
                message=message_text,
            )
            db.add(message)
            db.commit()
            db.refresh(message)

            write_audit_log(
                db,
                actor_user_id=user.id,
                actor_role=user.role,
                event_type="consultation_ws_message",
                target_type="consultation_ticket",
                target_id=str(ticket.id),
                severity=ticket.severity_level,
                metadata={"message_length": len(message_text)},
            )

            await manager.broadcast(
                ticket_id,
                {
                    "type": "message",
                    "ticket_id": ticket.id,
                    "sender_user_id": user.id,
                    "message": message.message,
                    "created_at": message.created_at.isoformat(),
                },
            )
    except WebSocketDisconnect:
        manager.disconnect(ticket_id, websocket)
    except Exception:
        try:
            await websocket.close(code=1011)
        finally:
            manager.disconnect(ticket_id, websocket)
    finally:
        db.close()


@router.get("/{ticket_id}/messages", response_model=list[ConsultationMessageResponse])
def get_consultation_messages(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = _get_ticket_or_404(db, ticket_id)
    _ensure_access(ticket, user)

    return (
        db.query(ConsultationMessage)
        .filter(ConsultationMessage.ticket_id == ticket.id)
        .order_by(ConsultationMessage.created_at.asc())
        .all()
    )


@router.post("/{ticket_id}/close", response_model=ConsultationTicketResponse)
def close_consultation(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = _get_ticket_or_404(db, ticket_id)
    _ensure_access(ticket, user)

    if ticket.status == "closed":
        return ticket

    ticket.status = "closed"
    ticket.closed_at = datetime.utcnow()

    if ticket.doctor_id:
        profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == ticket.doctor_id).first()
        if profile:
            profile.total_consultations += 1

    db.commit()
    db.refresh(ticket)

    write_audit_log(
        db,
        actor_user_id=user.id,
        actor_role=user.role,
        event_type="consultation_closed",
        target_type="consultation_ticket",
        target_id=str(ticket.id),
        severity=ticket.severity_level,
        metadata={"status": ticket.status},
    )
    return ticket


@router.post("/{ticket_id}/rate", status_code=status.HTTP_201_CREATED)
def rate_doctor(
    ticket_id: int,
    payload: DoctorRatingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("user")),
):
    ticket = _get_ticket_or_404(db, ticket_id)

    if ticket.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owner can rate this consultation")

    if ticket.status != "closed":
        raise HTTPException(status_code=400, detail="Consultation must be closed before rating")

    if not ticket.doctor_id:
        raise HTTPException(status_code=400, detail="No doctor was assigned")

    exists = db.query(DoctorRating).filter(DoctorRating.ticket_id == ticket.id).first()
    if exists:
        raise HTTPException(status_code=409, detail="This consultation is already rated")

    rating = DoctorRating(
        ticket_id=ticket.id,
        user_id=user.id,
        doctor_id=ticket.doctor_id,
        rating=payload.rating,
        review=payload.review,
    )
    db.add(rating)

    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == ticket.doctor_id).first()
    if profile:
        new_total = profile.total_ratings + 1
        profile.average_rating = (
            (profile.average_rating * profile.total_ratings) + payload.rating
        ) / new_total
        profile.total_ratings = new_total

    try:
        db.commit()
    except IntegrityError:
        # Two concurrent submissions both passed the exists-check above; the
        # DB's unique constraint on ticket_id is the real guard here.
        db.rollback()
        raise HTTPException(status_code=409, detail="This consultation is already rated")

    write_audit_log(
        db,
        actor_user_id=user.id,
        actor_role=user.role,
        event_type="doctor_rated",
        target_type="doctor_profile",
        target_id=str(ticket.doctor_id),
        severity="info",
        metadata={"ticket_id": ticket.id, "rating": payload.rating},
    )
    return {"ticket_id": ticket.id, "doctor_id": ticket.doctor_id, "rating": payload.rating}
