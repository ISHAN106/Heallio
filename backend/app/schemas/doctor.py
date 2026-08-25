from datetime import datetime

from pydantic import BaseModel, Field


class DoctorCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=300)


class DoctorCategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class DoctorProfileCreate(BaseModel):
    category_id: int
    license_number: str = Field(min_length=4, max_length=64)
    years_experience: int = Field(ge=0, le=60)
    bio: str | None = Field(default=None, max_length=500)
    is_available: bool = True


class DoctorProfileResponse(BaseModel):
    id: int
    user_id: int
    doctor_name: str
    category_id: int
    category_name: str
    license_number: str
    years_experience: int
    bio: str | None = None
    is_available: bool
    average_rating: float
    total_ratings: int
    total_consultations: int
    created_at: datetime
    avg_response_seconds: float | None = None
    active_cases: int = 0
    prescriptions_issued: int = 0


class DoctorReputationResponse(BaseModel):
    doctor_id: int
    average_rating: float
    total_ratings: int
    total_consultations: int
    category_name: str
