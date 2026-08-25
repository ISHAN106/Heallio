from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class DoctorCategory(Base):
    __tablename__ = "doctor_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    doctor_profiles = relationship("DoctorProfile", back_populates="category")


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    category_id = Column(Integer, ForeignKey("doctor_categories.id"), nullable=False)

    license_number = Column(String, nullable=False, unique=True, index=True)
    years_experience = Column(Integer, nullable=False, default=0)
    bio = Column(String, nullable=True)
    is_available = Column(Boolean, nullable=False, default=True)

    average_rating = Column(Float, nullable=False, default=0.0)
    total_ratings = Column(Integer, nullable=False, default=0)
    total_consultations = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="doctor_profile")
    category = relationship("DoctorCategory", back_populates="doctor_profiles")
