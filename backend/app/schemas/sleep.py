from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict

class SleepCreate(BaseModel):
    sleep_start: datetime
    sleep_end: datetime
    quality: str | None = Field(default=None, pattern="^(good|average|poor)$")

class SleepResponse(SleepCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}

class SleepSummaryResponse(BaseModel):
    days_tracked: int
    total_sleep_hours: float
    average_sleep_hours: float
    sleep_quality_breakdown: Dict[str, int]