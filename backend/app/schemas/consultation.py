from datetime import datetime

from pydantic import BaseModel, Field


class ConsultationCreateManual(BaseModel):
    reason: str = Field(min_length=5, max_length=800)
    category_name: str | None = Field(default=None, max_length=100)


class ConsultationMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ConsultationMessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender_user_id: int
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConsultationTicketResponse(BaseModel):
    id: int
    user_id: int
    doctor_id: int | None = None
    trigger_source: str
    trigger_reason: str
    severity_score: int
    severity_level: str
    status: str
    created_at: datetime
    accepted_at: datetime | None = None
    closed_at: datetime | None = None

    model_config = {"from_attributes": True}


class DoctorRatingCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    review: str | None = Field(default=None, max_length=400)
