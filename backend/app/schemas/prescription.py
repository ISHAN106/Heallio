from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


class PrescriptionItemCreate(BaseModel):
    medication_name: str = Field(min_length=1, max_length=200)
    dosage: str | None = Field(default=None, max_length=100)
    frequency: str | None = Field(default=None, max_length=100)
    duration: str | None = Field(default=None, max_length=100)
    instructions: str | None = Field(default=None, max_length=400)


class PrescriptionCreate(BaseModel):
    items: list[PrescriptionItemCreate] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=1000)
    follow_up_date: date | None = None

    @model_validator(mode="after")
    def _require_items_or_notes(self) -> "PrescriptionCreate":
        has_notes = self.notes is not None and self.notes.strip() != ""
        if not self.items and not has_notes:
            raise ValueError("A prescription needs at least one medication item or non-empty notes")
        return self


class PrescriptionItemResponse(PrescriptionItemCreate):
    id: int

    model_config = {"from_attributes": True}


class PrescriptionResponse(BaseModel):
    id: int
    ticket_id: int
    doctor_id: int
    user_id: int
    notes: str | None
    follow_up_date: date | None
    status: str
    supersedes_id: int | None
    created_at: datetime
    items: list[PrescriptionItemResponse]

    model_config = {"from_attributes": True}


class MyPrescriptionResponse(PrescriptionResponse):
    doctor_name: str
