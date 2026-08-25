from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class HealthRecord(Base):
    __tablename__ = "health_records"

    id = Column(Integer, primary_key=True, index=True)
    metric = Column(String, nullable=False)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ✅ FK
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="health_records")


class HealthMetricRecord(Base):
    """Wearable-style metrics written by the /health endpoints."""

    __tablename__ = "health_metric_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    steps = Column(Integer, nullable=True)
    heart_rate = Column(Float, nullable=True)
    calories_burned = Column(Float, nullable=True)
    systolic_bp = Column(Integer, nullable=True)
    diastolic_bp = Column(Integer, nullable=True)
    blood_glucose = Column(Float, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)