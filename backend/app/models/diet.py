from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class DietRecord(Base):
    __tablename__ = "diet_records"

    id = Column(Integer, primary_key=True, index=True)
    meal_type = Column(String, nullable=False)
    food = Column(String, nullable=False)
    calories = Column(Integer)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ✅ THIS IS CRITICAL
    user_id = Column(Integer, ForeignKey("users.id"))

    # ✅ relationship to User (NOT DietRecord)
    user = relationship("User", back_populates="diet_records")