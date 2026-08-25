import pytest
from pydantic import ValidationError

from app.schemas.prescription import PrescriptionCreate, PrescriptionItemCreate


def test_rejects_empty_submission():
    with pytest.raises(ValidationError):
        PrescriptionCreate(items=[], notes=None, follow_up_date=None)


def test_accepts_notes_only():
    payload = PrescriptionCreate(items=[], notes="Rest and hydrate", follow_up_date=None)
    assert payload.notes == "Rest and hydrate"
    assert payload.items == []


def test_accepts_items_only():
    payload = PrescriptionCreate(
        items=[PrescriptionItemCreate(medication_name="Paracetamol", dosage="500mg")],
        notes=None,
        follow_up_date=None,
    )
    assert len(payload.items) == 1
    assert payload.items[0].medication_name == "Paracetamol"
