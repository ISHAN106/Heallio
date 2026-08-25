from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DietCreate(BaseModel):
    meal_type: str = Field(min_length=2, max_length=50)
    food: str = Field(min_length=2, max_length=300)
    calories: Optional[int] = Field(default=None, ge=0, le=10000)
    notes: Optional[str] = Field(default=None, max_length=500)

class DietResponse(DietCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}