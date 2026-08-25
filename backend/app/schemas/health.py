from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class HealthCreate(BaseModel):
    heart_rate: Optional[int] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    weight: Optional[int] = None
    notes: Optional[str] = None

class HealthResponse(HealthCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
        
class HealthScoreResponse(BaseModel):
    health_score: int
    status: str
    message: str


class HealthMetricCreate(BaseModel):
    steps: Optional[int] = None
    heart_rate: Optional[float] = None
    calories_burned: Optional[float] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    blood_glucose: Optional[float] = None
    recorded_at: Optional[datetime] = None


class HealthMetricResponse(BaseModel):
    id: int
    user_id: int
    steps: Optional[int] = None
    heart_rate: Optional[float] = None
    calories_burned: Optional[float] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    blood_glucose: Optional[float] = None
    recorded_at: datetime

    model_config = {"from_attributes": True}
        

