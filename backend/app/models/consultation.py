from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ConsultationTicket(Base):
    __tablename__ = "consultation_tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    trigger_source = Column(String, nullable=False)  # chat | stats | manual
    trigger_reason = Column(Text, nullable=False)
    severity_score = Column(Integer, nullable=False)
    severity_level = Column(String, nullable=False)  # low | medium | high | critical
    status = Column(String, nullable=False, default="pending")

    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    user = relationship(
        "User",
        back_populates="consultation_tickets_created",
        foreign_keys=[user_id],
    )
    doctor = relationship(
        "User",
        back_populates="consultation_tickets_assigned",
        foreign_keys=[doctor_id],
    )
    messages = relationship(
        "ConsultationMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    rating = relationship(
        "DoctorRating",
        back_populates="ticket",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ConsultationMessage(Base):
    __tablename__ = "consultation_messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(
        Integer,
        ForeignKey("consultation_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("ConsultationTicket", back_populates="messages")


class DoctorRating(Base):
    __tablename__ = "doctor_ratings"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(
        Integer,
        ForeignKey("consultation_tickets.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    rating = Column(Integer, nullable=False)
    review = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("ConsultationTicket", back_populates="rating")
