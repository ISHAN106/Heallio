from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ConsentUpdateRequest(BaseModel):
    consent_given: bool
    consent_version: str = Field(default="v1", max_length=20)


class ConsentResponse(BaseModel):
    consent_given: bool
    consent_version: str
    granted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    updated_at: datetime


class DataDeletionRequestCreate(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)


class DataDeletionRequestResponse(BaseModel):
    id: int
    status: str
    reason: Optional[str] = None
    requested_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
