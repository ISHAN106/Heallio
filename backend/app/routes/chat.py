import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas.chat import ChatMetricsContext, ChatRequest, ChatResponse, ConsultationSuggestion
from ml.chatbot.health_context import get_health_context
from ml.chatbot.llm_engine import generate_reply
from ml.chatbot.safety import is_safe, get_safety_message
from app.database import get_db
from app.models.user import User
from app.models.chat import ChatMessage
from app.models.privacy import UserConsent
from app.services.audit import write_audit_log
from app.services.auth import get_current_user_email
from app.services.escalation import create_consultation_ticket, evaluate_chat_risk
from app.services.rate_limit import rate_limiter

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def chat(
    request: ChatRequest,
    raw_request: Request,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Send a message to the AI chatbot.
    
    Requires authentication. Returns AI response with multi-turn conversation support.
    
    - **message**: User's message to the chatbot
    """
    try:
        client_ip = raw_request.client.host if raw_request.client else "unknown"
        key = f"chat:{client_ip}"
        if not rate_limiter.allow(
            key,
            limit=settings.CHAT_RATE_LIMIT,
            window_seconds=settings.CHAT_RATE_WINDOW_SECONDS,
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many chat requests. Please slow down.",
            )

        # Get user from database
        user = db.query(User).filter(User.email == current_user_email).first()

        if not user:
            logger.error(f"Authenticated user not found in DB: {current_user_email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        consent = db.query(UserConsent).filter(UserConsent.user_id == user.id).first()
        if not consent or not consent.consent_given:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Privacy consent required before using chat",
            )

        # Load recent conversation history for the LLM's context
        history = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == user.id)
            .order_by(ChatMessage.id.desc())
            .limit(10)
            .all()
        )
        history.reverse()

        # Fetched once and shared with risk evaluation below — both need the
        # same 7-day sleep/diet averages, no need to query twice per message.
        health_context = get_health_context(db, current_user_email)

        # Get chatbot response
        if is_safe(request.message):
            reply = generate_reply(request.message, db, current_user_email, history, health_context)
        else:
            reply = get_safety_message(request.message)

        # Save chat message and response
        chat_entry = ChatMessage(
            user_id=user.id,
            message=request.message,
            response=reply,
        )

        db.add(chat_entry)
        db.commit()
        db.refresh(chat_entry)

        logger.info(f"Chat message saved for user {current_user_email}")

        risk = evaluate_chat_risk(db, user, request.message, health_context)

        if risk["severity_level"] == "critical":
            ticket = create_consultation_ticket(
                db,
                user=user,
                trigger_source="chat",
                trigger_reason=risk["reason"],
                severity_score=risk["severity_score"],
                category_name=risk["category_name"],
            )
            write_audit_log(
                db,
                actor_user_id=user.id,
                actor_role=user.role,
                event_type="chat_escalated",
                target_type="consultation_ticket",
                target_id=str(ticket.id),
                severity=ticket.severity_level,
                metadata={
                    "severity_score": risk["severity_score"],
                    "category_name": risk["category_name"],
                },
            )
            return ChatResponse(
                response=(
                    f"{reply}\n\n"
                    "I detected signs that may need professional attention. "
                    f"A consultation ticket #{ticket.id} has been opened."
                ),
                escalated=True,
                consultation_ticket_id=ticket.id,
                consultation_status=ticket.status,
                doctor_id=ticket.doctor_id,
                metrics_implicated=ChatMetricsContext(**risk["context"]),
            )

        if risk["severity_level"] in {"high", "medium"}:
            return ChatResponse(
                response=reply,
                consultation_suggestion=ConsultationSuggestion(
                    category_name=risk["category_name"],
                    severity_level=risk["severity_level"],
                    reason=risk["reason"],
                ),
                metrics_implicated=ChatMetricsContext(**risk["context"]),
            )

        return ChatResponse(response=reply)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat message",
        ) from e


@router.get("/history", status_code=status.HTTP_200_OK)
def chat_history(
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Return recent chat history for the authenticated user."""
    user = db.query(User).filter(User.email == current_user_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(100)
        .all()
    )

    return [
        {
            "id": row.id,
            "user_id": row.user_id,
            "message": row.message,
            "response": row.response,
            "timestamp": row.timestamp,
        }
        for row in rows
    ]