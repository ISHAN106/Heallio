from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")
    is_active = Column(Boolean, nullable=False, default=True)
    # Tokens issued before this timestamp are rejected (set on logout to revoke
    # all outstanding access + refresh tokens for the account).
    tokens_valid_from = Column(DateTime, nullable=True)

    # ✅ ONE user → MANY diet records
    diet_records = relationship("DietRecord", back_populates="user")

    # ✅ ONE user → MANY health records
    health_records = relationship("HealthRecord", back_populates="user")
    
    sleep_records = relationship("SleepRecord", back_populates="user")

    doctor_profile = relationship("DoctorProfile", back_populates="user", uselist=False)
    consultation_tickets_created = relationship(
        "ConsultationTicket",
        back_populates="user",
        foreign_keys="ConsultationTicket.user_id",
    )
    consultation_tickets_assigned = relationship(
        "ConsultationTicket",
        back_populates="doctor",
        foreign_keys="ConsultationTicket.doctor_id",
    )