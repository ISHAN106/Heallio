# Prescription / Care-Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a doctor attach a structured, immutable prescription/care-plan to an active consultation ticket, and let the patient see their prescription history.

**Architecture:** New `Prescription`/`PrescriptionItem` SQLAlchemy tables linked to the existing `ConsultationTicket`. A new `backend/app/routes/prescriptions.py` router exposes create/list/supersede endpoints, reusing the existing audit-log and WebSocket-broadcast patterns from `consultations.py`. On the Flutter side, new models, `ApiClient` methods, and Riverpod providers feed a shared `PrescriptionCard` widget used both inline in `ConsultationScreen` and in a new standalone `PrescriptionsScreen` reachable from `ProfileScreen`.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + pytest (backend); Flutter + Riverpod + `flutter_test` (frontend).

## Global Constraints

- Prescriptions are never updated in place — corrections go through a `supersede` endpoint that creates a new row and flips the old row's `status` to `superseded`. (Spec: Data model)
- A prescription must have at least one medication item OR non-empty `notes` — reject empty submissions with a 422. (Spec: Data model)
- Only the ticket's assigned doctor can create/supersede prescriptions on that ticket; only the ticket's patient or assigned doctor can read them. (Spec: Backend API)
- Creating a prescription requires `ticket.status` in `{"accepted", "in_progress"}` — 400 otherwise. (Spec: Backend API)
- No push notifications, no PDF export, no video/payment features — out of scope for this plan. (Spec: Non-goals)
- The "My Prescriptions" screen is reached from a `ProfileScreen` menu item, not a new bottom-nav tab. (Spec: Frontend)

---

### Task 1: Prescription & PrescriptionItem models

**Files:**
- Create: `backend/app/models/prescription.py`
- Modify: `backend/app/main.py:26` (add model import so `Base.metadata.create_all` picks up the new tables)
- Create: `backend/alembic/versions/0006_prescriptions.py`
- Test: `backend/tests/test_prescription_model.py`

**Interfaces:**
- Produces: `Prescription` (id, ticket_id, doctor_id, user_id, notes, follow_up_date, status, supersedes_id, created_at, `items` relationship) and `PrescriptionItem` (id, prescription_id, medication_name, dosage, frequency, duration, instructions) in `app.models.prescription`, used by every later task.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_prescription_model.py
from datetime import date

from app.database import SessionLocal
from app.models.consultation import ConsultationTicket
from app.models.prescription import Prescription, PrescriptionItem
from app.models.user import User


def _make_user(db, email: str, role: str) -> User:
    user = User(name=f"{role.title()} User", email=email, password="hashed", role=role)
    db.add(user)
    db.flush()
    return user


def test_prescription_with_items_persists_and_cascades():
    db = SessionLocal()
    try:
        patient = _make_user(db, "prescription-model-patient@example.com", "user")
        doctor = _make_user(db, "prescription-model-doctor@example.com", "doctor")
        ticket = ConsultationTicket(
            user_id=patient.id,
            doctor_id=doctor.id,
            trigger_source="manual",
            trigger_reason="test",
            severity_score=50,
            severity_level="medium",
            status="in_progress",
        )
        db.add(ticket)
        db.flush()

        prescription = Prescription(
            ticket_id=ticket.id,
            doctor_id=doctor.id,
            user_id=patient.id,
            notes="Rest and hydrate",
            follow_up_date=date(2026, 7, 20),
            status="active",
        )
        db.add(prescription)
        db.flush()

        item = PrescriptionItem(
            prescription_id=prescription.id,
            medication_name="Paracetamol",
            dosage="500mg",
            frequency="twice daily",
            duration="3 days",
        )
        db.add(item)
        db.commit()

        db.refresh(prescription)
        assert len(prescription.items) == 1
        assert prescription.items[0].medication_name == "Paracetamol"

        prescription_id = prescription.id
        db.delete(prescription)
        db.commit()

        assert db.query(PrescriptionItem).filter(PrescriptionItem.prescription_id == prescription_id).first() is None
    finally:
        db.query(User).filter(
            User.email.in_(["prescription-model-patient@example.com", "prescription-model-doctor@example.com"])
        ).delete(synchronize_session=False)
        db.commit()
        db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_prescription_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.prescription'`

- [ ] **Step 3: Write the model**

```python
# backend/app/models/prescription.py
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("consultation_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    notes = Column(Text, nullable=True)
    follow_up_date = Column(Date, nullable=True)
    status = Column(String, nullable=False, default="active")
    supersedes_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship(
        "PrescriptionItem",
        back_populates="prescription",
        cascade="all, delete-orphan",
    )


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False, index=True)

    medication_name = Column(String, nullable=False)
    dosage = Column(String, nullable=True)
    frequency = Column(String, nullable=True)
    duration = Column(String, nullable=True)
    instructions = Column(String, nullable=True)

    prescription = relationship("Prescription", back_populates="items")
```

Register the import in `backend/app/main.py` so `Base.metadata.create_all` (line 63) creates the new tables. Add this line after `import app.models.consultation` (currently line 26):

```python
import app.models.prescription
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_prescription_model.py -v`
Expected: PASS (2 assertions: item persisted, cascade delete removes it)

- [ ] **Step 5: Write the Alembic migration**

```python
# backend/alembic/versions/0006_prescriptions.py
"""prescriptions

Revision ID: 0006_prescriptions
Revises: 0005_audit_logs
Create Date: 2026-07-09 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "0006_prescriptions"
down_revision = "0005_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prescriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("consultation_tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("supersedes_id", sa.Integer(), sa.ForeignKey("prescriptions.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_prescriptions_id", "prescriptions", ["id"])
    op.create_index("ix_prescriptions_ticket_id", "prescriptions", ["ticket_id"])
    op.create_index("ix_prescriptions_doctor_id", "prescriptions", ["doctor_id"])
    op.create_index("ix_prescriptions_user_id", "prescriptions", ["user_id"])

    op.create_table(
        "prescription_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "prescription_id",
            sa.Integer(),
            sa.ForeignKey("prescriptions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("medication_name", sa.String(), nullable=False),
        sa.Column("dosage", sa.String(), nullable=True),
        sa.Column("frequency", sa.String(), nullable=True),
        sa.Column("duration", sa.String(), nullable=True),
        sa.Column("instructions", sa.String(), nullable=True),
    )
    op.create_index("ix_prescription_items_id", "prescription_items", ["id"])
    op.create_index("ix_prescription_items_prescription_id", "prescription_items", ["prescription_id"])


def downgrade() -> None:
    op.drop_index("ix_prescription_items_prescription_id", table_name="prescription_items")
    op.drop_index("ix_prescription_items_id", table_name="prescription_items")
    op.drop_table("prescription_items")

    op.drop_index("ix_prescriptions_user_id", table_name="prescriptions")
    op.drop_index("ix_prescriptions_doctor_id", table_name="prescriptions")
    op.drop_index("ix_prescriptions_ticket_id", table_name="prescriptions")
    op.drop_index("ix_prescriptions_id", table_name="prescriptions")
    op.drop_table("prescriptions")
```

(`down_revision = "0005_audit_logs"` is correct — confirmed against `backend/alembic/versions/0005_audit_logs.py:13`, which sets `revision = "0005_audit_logs"`.)

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/models/prescription.py app/main.py alembic/versions/0006_prescriptions.py tests/test_prescription_model.py
git commit -m "feat: add Prescription and PrescriptionItem models"
```

---

### Task 2: Prescription Pydantic schemas

**Files:**
- Create: `backend/app/schemas/prescription.py`
- Test: `backend/tests/test_prescription_schema.py`

**Interfaces:**
- Consumes: nothing (pure schema layer).
- Produces: `PrescriptionItemCreate`, `PrescriptionCreate`, `PrescriptionItemResponse`, `PrescriptionResponse`, `MyPrescriptionResponse` in `app.schemas.prescription`, used by Task 3-5's route handlers.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_prescription_schema.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_prescription_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.schemas.prescription'`

- [ ] **Step 3: Write the schemas**

```python
# backend/app/schemas/prescription.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_prescription_schema.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/schemas/prescription.py tests/test_prescription_schema.py
git commit -m "feat: add prescription request/response schemas"
```

---

### Task 3: Create-prescription endpoint

**Files:**
- Create: `backend/app/routes/prescriptions.py`
- Modify: `backend/app/main.py:37` (import), `backend/app/main.py:180` (register router)
- Test: `backend/tests/test_prescriptions.py`

**Interfaces:**
- Consumes: `Prescription`, `PrescriptionItem` (Task 1); `PrescriptionCreate`, `PrescriptionResponse` (Task 2); `write_audit_log` (`app.services.audit`, signature: `write_audit_log(db, *, actor_user_id, actor_role, event_type, target_type=None, target_id=None, severity="info", metadata=None)`); `require_role`, `get_current_user` (`app.services.auth`); `manager.broadcast(ticket_id: int, payload: dict)` (`app.services.consultation_ws`, async).
- Produces: `router` (`APIRouter`) in `app.routes.prescriptions`, mounted in `main.py`. Endpoint `POST /consultations/{ticket_id}/prescriptions` used by Task 6's `ApiClient.createPrescription`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_prescriptions.py
def _signup_and_login(client, email: str, password: str, role: str = "user"):
    client.post(
        "/users/signup",
        json={"name": f"{role.title()} User", "email": email, "password": password, "role": role},
    )
    login = client.post(
        "/users/login",
        data={"username": email, "password": password, "role": role},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return login.json()["access_token"]


def _grant_consent(client, token: str):
    client.post(
        "/privacy/consent",
        json={"consent_given": True, "consent_version": "v1"},
        headers={"Authorization": f"Bearer {token}"},
    )


def _create_accepted_ticket(client, patient_email, doctor_email):
    patient_token = _signup_and_login(client, patient_email, "StrongPass1!", "user")
    _grant_consent(client, patient_token)
    doctor_token = _signup_and_login(client, doctor_email, "StrongPass1!", "doctor")

    ticket = client.post(
        "/consultations/manual",
        json={"reason": "Persistent headache", "category_name": "General Physician"},
        headers={"Authorization": f"Bearer {patient_token}"},
    ).json()

    client.post(
        f"/consultations/{ticket['id']}/accept",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    return ticket["id"], patient_token, doctor_token


def test_doctor_can_create_prescription(client, random_email):
    ticket_id, patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )

    response = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={
            "items": [{"medication_name": "Paracetamol", "dosage": "500mg", "frequency": "twice daily"}],
            "notes": "Drink plenty of fluids",
            "follow_up_date": "2026-07-20",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "active"
    assert body["notes"] == "Drink plenty of fluids"
    assert len(body["items"]) == 1
    assert body["items"][0]["medication_name"] == "Paracetamol"


def test_patient_cannot_create_prescription(client, random_email):
    ticket_id, patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )

    response = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Self-prescribing", "follow_up_date": None},
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert response.status_code == 403


def test_unassigned_doctor_cannot_create_prescription(client, random_email):
    ticket_id, _patient_token, _doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    other_doctor_token = _signup_and_login(client, f"other-doctor-{random_email}", "StrongPass1!", "doctor")

    response = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Not my patient", "follow_up_date": None},
        headers={"Authorization": f"Bearer {other_doctor_token}"},
    )
    assert response.status_code == 403


def test_cannot_create_prescription_on_pending_ticket(client, random_email):
    patient_token = _signup_and_login(client, f"patient-{random_email}", "StrongPass1!", "user")
    _grant_consent(client, patient_token)
    doctor_token = _signup_and_login(client, f"doctor-{random_email}", "StrongPass1!", "doctor")

    ticket = client.post(
        "/consultations/manual",
        json={"reason": "Persistent headache", "category_name": "General Physician"},
        headers={"Authorization": f"Bearer {patient_token}"},
    ).json()

    response = client.post(
        f"/consultations/{ticket['id']}/prescriptions",
        json={"items": [], "notes": "No doctor assigned yet", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 400


def test_cannot_create_prescription_on_closed_ticket(client, random_email):
    ticket_id, patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    client.post(f"/consultations/{ticket_id}/close", headers={"Authorization": f"Bearer {doctor_token}"})

    response = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Too late", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 400


def test_empty_submission_rejected(client, random_email):
    ticket_id, _patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )

    response = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": None, "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_prescriptions.py -v`
Expected: FAIL with 404s (no route registered yet)

- [ ] **Step 3: Write the route**

```python
# backend/app/routes/prescriptions.py
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.consultation import ConsultationTicket
from app.models.prescription import Prescription, PrescriptionItem
from app.models.user import User
from app.schemas.prescription import PrescriptionCreate, PrescriptionResponse
from app.services.audit import write_audit_log
from app.services.auth import require_role
from app.services.consultation_ws import manager

router = APIRouter(tags=["Prescriptions"])


def _get_ticket_or_404(db: Session, ticket_id: int) -> ConsultationTicket:
    ticket = db.query(ConsultationTicket).filter(ConsultationTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Consultation not found")
    return ticket


def _ensure_assigned_doctor(ticket: ConsultationTicket, doctor: User) -> None:
    if ticket.doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="Not the assigned doctor for this consultation")


@router.post(
    "/consultations/{ticket_id}/prescriptions",
    response_model=PrescriptionResponse,
    status_code=201,
)
async def create_prescription(
    ticket_id: int,
    payload: PrescriptionCreate,
    db: Session = Depends(get_db),
    doctor: User = Depends(require_role("doctor")),
):
    ticket = _get_ticket_or_404(db, ticket_id)

    if ticket.status not in ("accepted", "in_progress"):
        raise HTTPException(status_code=400, detail="Consultation must be active to add a prescription")

    _ensure_assigned_doctor(ticket, doctor)

    prescription = Prescription(
        ticket_id=ticket.id,
        doctor_id=doctor.id,
        user_id=ticket.user_id,
        notes=payload.notes,
        follow_up_date=payload.follow_up_date,
        status="active",
    )
    db.add(prescription)
    db.flush()

    for item in payload.items:
        db.add(
            PrescriptionItem(
                prescription_id=prescription.id,
                medication_name=item.medication_name,
                dosage=item.dosage,
                frequency=item.frequency,
                duration=item.duration,
                instructions=item.instructions,
            )
        )

    db.commit()
    db.refresh(prescription)

    write_audit_log(
        db,
        actor_user_id=doctor.id,
        actor_role=doctor.role,
        event_type="prescription_created",
        target_type="prescription",
        target_id=str(prescription.id),
        severity="info",
        metadata={"ticket_id": ticket.id, "item_count": len(payload.items)},
    )

    await manager.broadcast(
        ticket.id,
        {
            "type": "system",
            "ticket_id": ticket.id,
            "message": "prescription_added",
            "prescription_id": prescription.id,
        },
    )

    return prescription
```

Wire it into `backend/app/main.py`. After the existing import (currently line 37):

```python
from app.routes import consultations as consultations_routes
```

add:

```python
from app.routes import prescriptions as prescriptions_routes
```

After the existing registration (currently line 180):

```python
app.include_router(consultations_routes.router, tags=["Consultations"])
```

add:

```python
app.include_router(prescriptions_routes.router, tags=["Prescriptions"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_prescriptions.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/routes/prescriptions.py app/main.py tests/test_prescriptions.py
git commit -m "feat: add POST /consultations/{ticket_id}/prescriptions endpoint"
```

---

### Task 4: List endpoints (per-ticket and patient history)

**Files:**
- Modify: `backend/app/routes/prescriptions.py`
- Test: `backend/tests/test_prescriptions.py`

**Interfaces:**
- Consumes: everything from Task 3, plus `MyPrescriptionResponse` (Task 2), `get_current_user` (`app.services.auth`).
- Produces: `GET /consultations/{ticket_id}/prescriptions` and `GET /prescriptions/my`, used by Task 7's `ApiClient.getTicketPrescriptions` / `getMyPrescriptions`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_prescriptions.py`:

```python
def test_ticket_prescriptions_visible_to_patient_and_doctor(client, random_email):
    ticket_id, patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Rest", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )

    for token in (patient_token, doctor_token):
        response = client.get(
            f"/consultations/{ticket_id}/prescriptions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert len(response.json()) == 1


def test_ticket_prescriptions_hidden_from_non_participant(client, random_email):
    ticket_id, _patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Rest", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    outsider_token = _signup_and_login(client, f"outsider-{random_email}", "StrongPass1!", "user")

    response = client.get(
        f"/consultations/{ticket_id}/prescriptions",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert response.status_code == 403


def test_my_prescriptions_lists_doctor_name(client, random_email):
    ticket_id, patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Rest", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )

    response = client.get(
        "/prescriptions/my",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["doctor_name"] == "Doctor User"
    assert body[0]["ticket_id"] == ticket_id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_prescriptions.py -v`
Expected: FAIL with 404s for the two new routes

- [ ] **Step 3: Add the list endpoints**

Add to `backend/app/routes/prescriptions.py` (after the imports, add `get_current_user`; after `create_prescription`, add these two handlers):

```python
from app.services.auth import get_current_user, require_role
```

(replace the existing `from app.services.auth import require_role` line with the one above)

```python
def _ensure_participant(ticket: ConsultationTicket, user: User) -> None:
    if user.id not in {ticket.user_id, ticket.doctor_id}:
        raise HTTPException(status_code=403, detail="Not allowed to view this consultation's prescriptions")


@router.get(
    "/consultations/{ticket_id}/prescriptions",
    response_model=list[PrescriptionResponse],
)
def list_ticket_prescriptions(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = _get_ticket_or_404(db, ticket_id)
    _ensure_participant(ticket, user)

    return (
        db.query(Prescription)
        .filter(Prescription.ticket_id == ticket.id)
        .order_by(Prescription.created_at.desc())
        .all()
    )


@router.get("/prescriptions/my", response_model=list[MyPrescriptionResponse])
def list_my_prescriptions(
    db: Session = Depends(get_db),
    patient: User = Depends(require_role("user")),
):
    prescriptions = (
        db.query(Prescription)
        .filter(Prescription.user_id == patient.id)
        .order_by(Prescription.created_at.desc())
        .all()
    )

    doctor_ids = {p.doctor_id for p in prescriptions}
    doctor_names = {
        d.id: d.name for d in db.query(User).filter(User.id.in_(doctor_ids)).all()
    }

    return [
        MyPrescriptionResponse(
            **PrescriptionResponse.model_validate(p).model_dump(),
            doctor_name=doctor_names.get(p.doctor_id, "Unknown"),
        )
        for p in prescriptions
    ]
```

Also update the import line for `PrescriptionResponse` to include the new schema:

```python
from app.schemas.prescription import MyPrescriptionResponse, PrescriptionCreate, PrescriptionResponse
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_prescriptions.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/routes/prescriptions.py tests/test_prescriptions.py
git commit -m "feat: add prescription list endpoints for ticket and patient history"
```

---

### Task 5: Supersede endpoint

**Files:**
- Modify: `backend/app/routes/prescriptions.py`
- Test: `backend/tests/test_prescriptions.py`

**Interfaces:**
- Consumes: everything from Tasks 3-4.
- Produces: `POST /prescriptions/{id}/supersede`, used by Task 7's `ApiClient.supersedePrescription`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_prescriptions.py`:

```python
def test_doctor_can_supersede_prescription(client, random_email):
    ticket_id, patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    original = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={
            "items": [{"medication_name": "Paracetamol", "dosage": "500mg"}],
            "notes": None,
            "follow_up_date": None,
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    ).json()

    response = client.post(
        f"/prescriptions/{original['id']}/supersede",
        json={
            "items": [{"medication_name": "Paracetamol", "dosage": "1000mg"}],
            "notes": "Dosage increased",
            "follow_up_date": None,
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 201
    corrected = response.json()
    assert corrected["status"] == "active"
    assert corrected["supersedes_id"] == original["id"]
    assert corrected["items"][0]["dosage"] == "1000mg"

    ticket_prescriptions = client.get(
        f"/consultations/{ticket_id}/prescriptions",
        headers={"Authorization": f"Bearer {patient_token}"},
    ).json()
    statuses = {p["id"]: p["status"] for p in ticket_prescriptions}
    assert statuses[original["id"]] == "superseded"
    assert statuses[corrected["id"]] == "active"


def test_cannot_supersede_already_superseded_prescription(client, random_email):
    ticket_id, _patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    original = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Rest", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    ).json()
    client.post(
        f"/prescriptions/{original['id']}/supersede",
        json={"items": [], "notes": "Rest more", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )

    response = client.post(
        f"/prescriptions/{original['id']}/supersede",
        json={"items": [], "notes": "Again", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 400


def test_other_doctor_cannot_supersede(client, random_email):
    ticket_id, _patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    original = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Rest", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    ).json()
    other_doctor_token = _signup_and_login(client, f"other-doctor-{random_email}", "StrongPass1!", "doctor")

    response = client.post(
        f"/prescriptions/{original['id']}/supersede",
        json={"items": [], "notes": "Not mine", "follow_up_date": None},
        headers={"Authorization": f"Bearer {other_doctor_token}"},
    )
    assert response.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_prescriptions.py -v`
Expected: FAIL with 404 (route not registered yet)

- [ ] **Step 3: Add the supersede endpoint**

Add to `backend/app/routes/prescriptions.py`:

```python
def _get_prescription_or_404(db: Session, prescription_id: int) -> Prescription:
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return prescription


@router.post(
    "/prescriptions/{prescription_id}/supersede",
    response_model=PrescriptionResponse,
    status_code=201,
)
async def supersede_prescription(
    prescription_id: int,
    payload: PrescriptionCreate,
    db: Session = Depends(get_db),
    doctor: User = Depends(require_role("doctor")),
):
    old = _get_prescription_or_404(db, prescription_id)
    if old.doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="Not the doctor who issued this prescription")
    if old.status == "superseded":
        raise HTTPException(status_code=400, detail="This prescription has already been superseded")

    old.status = "superseded"

    new_prescription = Prescription(
        ticket_id=old.ticket_id,
        doctor_id=doctor.id,
        user_id=old.user_id,
        notes=payload.notes,
        follow_up_date=payload.follow_up_date,
        status="active",
        supersedes_id=old.id,
    )
    db.add(new_prescription)
    db.flush()

    for item in payload.items:
        db.add(
            PrescriptionItem(
                prescription_id=new_prescription.id,
                medication_name=item.medication_name,
                dosage=item.dosage,
                frequency=item.frequency,
                duration=item.duration,
                instructions=item.instructions,
            )
        )

    db.commit()
    db.refresh(new_prescription)

    write_audit_log(
        db,
        actor_user_id=doctor.id,
        actor_role=doctor.role,
        event_type="prescription_superseded",
        target_type="prescription",
        target_id=str(new_prescription.id),
        severity="info",
        metadata={"ticket_id": old.ticket_id, "supersedes_id": old.id},
    )

    await manager.broadcast(
        old.ticket_id,
        {
            "type": "system",
            "ticket_id": old.ticket_id,
            "message": "prescription_superseded",
            "prescription_id": new_prescription.id,
        },
    )

    return new_prescription
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_prescriptions.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && python -m pytest -v`
Expected: PASS (all existing tests plus the new ones — confirms no regression)

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/routes/prescriptions.py tests/test_prescriptions.py
git commit -m "feat: add prescription supersede endpoint"
```

---

### Task 6: Flutter models

**Files:**
- Modify: `health_app/lib/models/models.dart`
- Test: `health_app/test/prescription_model_test.dart`

**Interfaces:**
- Produces: `Prescription`, `PrescriptionItem` classes with `fromJson` factories in `health_app/lib/models/models.dart`, used by Task 7's `ApiClient` methods and Task 8's `PrescriptionCard`.

- [ ] **Step 1: Write the failing test**

```dart
// health_app/test/prescription_model_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:health_app/models/models.dart';

void main() {
  group('Prescription.fromJson', () {
    test('parses items, notes, and follow-up date', () {
      final prescription = Prescription.fromJson({
        'id': 1,
        'ticket_id': 7,
        'doctor_id': 3,
        'user_id': 9,
        'notes': 'Rest and hydrate',
        'follow_up_date': '2026-07-20',
        'status': 'active',
        'supersedes_id': null,
        'created_at': '2026-07-09T00:00:00.000Z',
        'items': [
          {
            'id': 1,
            'medication_name': 'Paracetamol',
            'dosage': '500mg',
            'frequency': 'twice daily',
            'duration': '3 days',
            'instructions': null,
          }
        ],
      });

      expect(prescription.id, '1');
      expect(prescription.status, 'active');
      expect(prescription.notes, 'Rest and hydrate');
      expect(prescription.followUpDate, DateTime.parse('2026-07-20'));
      expect(prescription.items.length, 1);
      expect(prescription.items.first.medicationName, 'Paracetamol');
      expect(prescription.items.first.dosage, '500mg');
    });

    test('parses a superseded prescription with no items', () {
      final prescription = Prescription.fromJson({
        'id': 2,
        'ticket_id': 7,
        'doctor_id': 3,
        'user_id': 9,
        'notes': null,
        'follow_up_date': null,
        'status': 'superseded',
        'supersedes_id': null,
        'created_at': '2026-07-09T00:00:00.000Z',
        'items': [],
      });

      expect(prescription.status, 'superseded');
      expect(prescription.followUpDate, isNull);
      expect(prescription.items, isEmpty);
    });
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd health_app && flutter test test/prescription_model_test.dart`
Expected: FAIL — `Prescription` isn't defined

- [ ] **Step 3: Add the models**

Append to `health_app/lib/models/models.dart` (after the `ConsultationMessageItem` class, currently ending around line 274):

```dart
class PrescriptionItem {
  final String id;
  final String medicationName;
  final String? dosage;
  final String? frequency;
  final String? duration;
  final String? instructions;

  PrescriptionItem({
    required this.id,
    required this.medicationName,
    required this.dosage,
    required this.frequency,
    required this.duration,
    required this.instructions,
  });

  factory PrescriptionItem.fromJson(Map<String, dynamic> json) {
    return PrescriptionItem(
      id: (json['id'] ?? '').toString(),
      medicationName: (json['medication_name'] ?? '').toString(),
      dosage: json['dosage']?.toString(),
      frequency: json['frequency']?.toString(),
      duration: json['duration']?.toString(),
      instructions: json['instructions']?.toString(),
    );
  }
}

class Prescription {
  final String id;
  final String ticketId;
  final String doctorId;
  final String userId;
  final String? notes;
  final DateTime? followUpDate;
  final String status;
  final String? supersedesId;
  final DateTime createdAt;
  final List<PrescriptionItem> items;
  final String? doctorName;

  Prescription({
    required this.id,
    required this.ticketId,
    required this.doctorId,
    required this.userId,
    required this.notes,
    required this.followUpDate,
    required this.status,
    required this.supersedesId,
    required this.createdAt,
    required this.items,
    this.doctorName,
  });

  bool get isActive => status == 'active';

  factory Prescription.fromJson(Map<String, dynamic> json) {
    return Prescription(
      id: (json['id'] ?? '').toString(),
      ticketId: (json['ticket_id'] ?? '').toString(),
      doctorId: (json['doctor_id'] ?? '').toString(),
      userId: (json['user_id'] ?? '').toString(),
      notes: json['notes']?.toString(),
      followUpDate: json['follow_up_date'] != null ? DateTime.parse(json['follow_up_date'].toString()) : null,
      status: (json['status'] ?? '').toString(),
      supersedesId: json['supersedes_id']?.toString(),
      createdAt: DateTime.parse((json['created_at'] ?? DateTime.now().toIso8601String()).toString()),
      items: ((json['items'] as List?) ?? const [])
          .map((item) => PrescriptionItem.fromJson(item as Map<String, dynamic>))
          .toList(),
      doctorName: json['doctor_name']?.toString(),
    );
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd health_app && flutter test test/prescription_model_test.dart`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
cd health_app
git add lib/models/models.dart test/prescription_model_test.dart
git commit -m "feat: add Prescription and PrescriptionItem Flutter models"
```

---

### Task 7: ApiClient methods and providers

**Files:**
- Modify: `health_app/lib/services/api_client.dart`
- Modify: `health_app/lib/providers/app_providers.dart`

**Interfaces:**
- Consumes: `Prescription.fromJson` (Task 6); backend routes from Tasks 3-5.
- Produces: `ApiClient.createPrescription`, `ApiClient.getTicketPrescriptions`, `ApiClient.getMyPrescriptions`, `ApiClient.supersedePrescription`; `ticketPrescriptionsProvider` (family, keyed by ticket id), `myPrescriptionsProvider` — used by Tasks 9-11.

- [ ] **Step 1: Add the ApiClient methods**

Add to `health_app/lib/services/api_client.dart`, directly after `rateDoctor` (currently ending at line 385):

```dart
  static Future<Prescription> createPrescription(
    String ticketId, {
    required List<Map<String, String?>> items,
    String? notes,
    String? followUpDate,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/consultations/$ticketId/prescriptions'),
      headers: {
        'Authorization': 'Bearer $_accessToken',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'items': items,
        'notes': notes,
        'follow_up_date': followUpDate,
      }),
    );
    if (response.statusCode == 201) {
      return Prescription.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    }
    throw Exception('Failed to create prescription: ${response.body}');
  }

  static Future<List<Prescription>> getTicketPrescriptions(String ticketId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/consultations/$ticketId/prescriptions'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List;
      return data.map((item) => Prescription.fromJson(item as Map<String, dynamic>)).toList();
    }
    throw Exception('Failed to load prescriptions for this consultation');
  }

  static Future<List<Prescription>> getMyPrescriptions() async {
    final response = await http.get(
      Uri.parse('$baseUrl/prescriptions/my'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List;
      return data.map((item) => Prescription.fromJson(item as Map<String, dynamic>)).toList();
    }
    throw Exception('Failed to load your prescriptions');
  }

  static Future<Prescription> supersedePrescription(
    String prescriptionId, {
    required List<Map<String, String?>> items,
    String? notes,
    String? followUpDate,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/prescriptions/$prescriptionId/supersede'),
      headers: {
        'Authorization': 'Bearer $_accessToken',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'items': items,
        'notes': notes,
        'follow_up_date': followUpDate,
      }),
    );
    if (response.statusCode == 201) {
      return Prescription.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    }
    throw Exception('Failed to supersede prescription: ${response.body}');
  }
```

- [ ] **Step 2: Add the providers**

Add to `health_app/lib/providers/app_providers.dart`, directly after `consultationMessagesProvider` (currently ending at line 200):

```dart
final ticketPrescriptionsProvider =
    FutureProvider.family<List<Prescription>, String>((ref, ticketId) async {
  return await ApiClient.getTicketPrescriptions(ticketId);
});

final myPrescriptionsProvider = FutureProvider<List<Prescription>>((ref) async {
  return await ApiClient.getMyPrescriptions();
});
```

- [ ] **Step 3: Verify the project still analyzes cleanly**

Run: `cd health_app && flutter analyze lib/services/api_client.dart lib/providers/app_providers.dart`
Expected: `No issues found!`

- [ ] **Step 4: Commit**

```bash
cd health_app
git add lib/services/api_client.dart lib/providers/app_providers.dart
git commit -m "feat: add ApiClient methods and providers for prescriptions"
```

---

### Task 8: PrescriptionCard widget

**Files:**
- Create: `health_app/lib/widgets/prescription_card.dart`

**Interfaces:**
- Consumes: `Prescription`, `PrescriptionItem` (Task 6); `StatusPill`, `StatusPillTone` (`health_app/lib/widgets/status_pill.dart`); `AppCard`, `AppColors` (`health_app/lib/widgets/common_widgets.dart`, `health_app/lib/theme/app_theme.dart`).
- Produces: `PrescriptionCard` widget (`prescription`, `onSupersede` optional callback), used by Tasks 10-11.

- [ ] **Step 1: Write the widget**

```dart
// health_app/lib/widgets/prescription_card.dart
import 'package:flutter/material.dart';

import '../models/models.dart';
import '../theme/app_theme.dart';
import 'common_widgets.dart';
import 'status_pill.dart';

class PrescriptionCard extends StatelessWidget {
  const PrescriptionCard({
    super.key,
    required this.prescription,
    this.onSupersede,
  });

  final Prescription prescription;
  final VoidCallback? onSupersede;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  prescription.doctorName != null ? 'From ${prescription.doctorName}' : 'Prescription',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
              ),
              StatusPill(
                label: prescription.status.toUpperCase(),
                tone: prescription.isActive ? StatusPillTone.success : StatusPillTone.neutral,
              ),
            ],
          ),
          if (prescription.items.isNotEmpty) ...[
            const SizedBox(height: 12),
            ...prescription.items.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(
                  [item.medicationName, item.dosage, item.frequency, item.duration]
                      .where((part) => part != null && part.isNotEmpty)
                      .join(' • '),
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
            ),
          ],
          if (prescription.notes != null && prescription.notes!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              prescription.notes!,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.grey500),
            ),
          ],
          if (prescription.followUpDate != null) ...[
            const SizedBox(height: 8),
            Text(
              'Follow up by ${prescription.followUpDate!.toLocal().toString().split(' ').first}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.grey500),
            ),
          ],
          if (onSupersede != null && prescription.isActive) ...[
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: onSupersede,
                child: const Text('Supersede with correction'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
```

- [ ] **Step 2: Verify the project still analyzes cleanly**

Run: `cd health_app && flutter analyze lib/widgets/prescription_card.dart`
Expected: `No issues found!`

- [ ] **Step 3: Commit**

```bash
cd health_app
git add lib/widgets/prescription_card.dart
git commit -m "feat: add PrescriptionCard widget"
```

---

### Task 9: PrescriptionFormScreen

**Files:**
- Create: `health_app/lib/screens/consultation/prescription_form_screen.dart`

**Interfaces:**
- Consumes: `ApiClient.createPrescription`, `ApiClient.supersedePrescription` (Task 7); `ticketPrescriptionsProvider` (Task 7, for invalidation); `AppColors`, `AppCard` (existing).
- Produces: `PrescriptionFormScreen` (`ticketId` required, `supersedesPrescriptionId` optional — when set, the form submits via supersede instead of create), used by Task 10.

- [ ] **Step 1: Write the screen**

```dart
// health_app/lib/screens/consultation/prescription_form_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/app_providers.dart';
import '../../services/api_client.dart';
import '../../theme/app_theme.dart';

class _MedicationRow {
  final TextEditingController name = TextEditingController();
  final TextEditingController dosage = TextEditingController();
  final TextEditingController frequency = TextEditingController();
  final TextEditingController duration = TextEditingController();

  void dispose() {
    name.dispose();
    dosage.dispose();
    frequency.dispose();
    duration.dispose();
  }
}

class PrescriptionFormScreen extends ConsumerStatefulWidget {
  const PrescriptionFormScreen({
    super.key,
    required this.ticketId,
    this.supersedesPrescriptionId,
  });

  final String ticketId;
  final String? supersedesPrescriptionId;

  @override
  ConsumerState<PrescriptionFormScreen> createState() => _PrescriptionFormScreenState();
}

class _PrescriptionFormScreenState extends ConsumerState<PrescriptionFormScreen> {
  final List<_MedicationRow> _rows = [_MedicationRow()];
  final TextEditingController _notesController = TextEditingController();
  DateTime? _followUpDate;
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    for (final row in _rows) {
      row.dispose();
    }
    _notesController.dispose();
    super.dispose();
  }

  void _addRow() {
    setState(() => _rows.add(_MedicationRow()));
  }

  void _removeRow(int index) {
    setState(() {
      _rows[index].dispose();
      _rows.removeAt(index);
    });
  }

  Future<void> _pickFollowUpDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) {
      setState(() => _followUpDate = picked);
    }
  }

  Future<void> _submit() async {
    final items = _rows
        .where((row) => row.name.text.trim().isNotEmpty)
        .map((row) => {
              'medication_name': row.name.text.trim(),
              'dosage': row.dosage.text.trim().isEmpty ? null : row.dosage.text.trim(),
              'frequency': row.frequency.text.trim().isEmpty ? null : row.frequency.text.trim(),
              'duration': row.duration.text.trim().isEmpty ? null : row.duration.text.trim(),
            })
        .toList();
    final notes = _notesController.text.trim().isEmpty ? null : _notesController.text.trim();

    if (items.isEmpty && notes == null) {
      setState(() => _error = 'Add at least one medication or a note before submitting.');
      return;
    }

    setState(() {
      _submitting = true;
      _error = null;
    });

    try {
      final followUpDateString = _followUpDate?.toIso8601String().split('T').first;
      if (widget.supersedesPrescriptionId != null) {
        await ApiClient.supersedePrescription(
          widget.supersedesPrescriptionId!,
          items: items,
          notes: notes,
          followUpDate: followUpDateString,
        );
      } else {
        await ApiClient.createPrescription(
          widget.ticketId,
          items: items,
          notes: notes,
          followUpDate: followUpDateString,
        );
      }
      ref.invalidate(ticketPrescriptionsProvider(widget.ticketId));
      ref.invalidate(myPrescriptionsProvider);
      if (!mounted) return;
      Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.supersedesPrescriptionId != null ? 'Supersede Prescription' : 'Add Prescription'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Medications', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          for (int i = 0; i < _rows.length; i++) ...[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    children: [
                      TextField(
                        controller: _rows[i].name,
                        decoration: const InputDecoration(labelText: 'Medication name'),
                      ),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _rows[i].dosage,
                              decoration: const InputDecoration(labelText: 'Dosage'),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: TextField(
                              controller: _rows[i].frequency,
                              decoration: const InputDecoration(labelText: 'Frequency'),
                            ),
                          ),
                        ],
                      ),
                      TextField(
                        controller: _rows[i].duration,
                        decoration: const InputDecoration(labelText: 'Duration'),
                      ),
                    ],
                  ),
                ),
                if (_rows.length > 1)
                  IconButton(
                    icon: const Icon(Icons.remove_circle_outline, color: AppColors.error),
                    onPressed: () => _removeRow(i),
                  ),
              ],
            ),
            const Divider(height: 24),
          ],
          TextButton.icon(
            onPressed: _addRow,
            icon: const Icon(Icons.add),
            label: const Text('Add another medication'),
          ),
          const SizedBox(height: 16),
          Text('Care instructions', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          TextField(
            controller: _notesController,
            maxLines: 3,
            decoration: const InputDecoration(hintText: 'Optional notes for the patient'),
          ),
          const SizedBox(height: 16),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(_followUpDate == null
                ? 'No follow-up date'
                : 'Follow up on ${_followUpDate!.toLocal().toString().split(' ').first}'),
            trailing: TextButton(onPressed: _pickFollowUpDate, child: const Text('Pick date')),
          ),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(_error!, style: const TextStyle(color: AppColors.error)),
          ],
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _submitting ? null : _submit,
              child: _submitting
                  ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Submit'),
            ),
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 2: Verify the project still analyzes cleanly**

Run: `cd health_app && flutter analyze lib/screens/consultation/prescription_form_screen.dart`
Expected: `No issues found!`

- [ ] **Step 3: Commit**

```bash
cd health_app
git add lib/screens/consultation/prescription_form_screen.dart
git commit -m "feat: add PrescriptionFormScreen for creating and superseding prescriptions"
```

---

### Task 10: Wire prescriptions into ConsultationScreen

**Files:**
- Modify: `health_app/lib/screens/consultation/consultation_screen.dart`

**Interfaces:**
- Consumes: `ticketPrescriptionsProvider` (Task 7), `PrescriptionCard` (Task 8), `PrescriptionFormScreen` (Task 9).

- [ ] **Step 1: Add the import and prescriptions section**

In `health_app/lib/screens/consultation/consultation_screen.dart`, add imports after the existing `status_pill.dart` import (currently line 8):

```dart
import '../../widgets/prescription_card.dart';
import 'prescription_form_screen.dart';
```

In the `build` method, after the existing `canClose` computation (currently line 131), add:

```dart
    final canAddPrescription = isDoctor && _ticket.doctorId == currentUser?.id && (_ticket.status == 'accepted' || _ticket.status == 'in_progress');
```

In the `body: ListView(...)` children list, immediately after the "Open Chat" `Card` block (currently ending at line 209, right before the `if (_ticket.status == 'closed' && !isDoctor)` block), insert:

```dart
          const SizedBox(height: 16),
          if (canAddPrescription)
            Card(
              child: ListTile(
                leading: const Icon(Icons.medication_outlined),
                title: const Text('Add Prescription'),
                subtitle: const Text('Record medications or care instructions for this consult'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => PrescriptionFormScreen(ticketId: _ticket.id),
                    ),
                  );
                },
              ),
            ),
          const SizedBox(height: 16),
          Consumer(
            builder: (context, ref, _) {
              final prescriptionsAsync = ref.watch(ticketPrescriptionsProvider(_ticket.id));
              return prescriptionsAsync.when(
                data: (prescriptions) {
                  if (prescriptions.isEmpty) return const SizedBox.shrink();
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Prescriptions', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      ...prescriptions.map(
                        (prescription) => Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: PrescriptionCard(
                            prescription: prescription,
                            onSupersede: isDoctor && _ticket.doctorId == currentUser?.id
                                ? () {
                                    Navigator.of(context).push(
                                      MaterialPageRoute(
                                        builder: (_) => PrescriptionFormScreen(
                                          ticketId: _ticket.id,
                                          supersedesPrescriptionId: prescription.id,
                                        ),
                                      ),
                                    );
                                  }
                                : null,
                          ),
                        ),
                      ),
                    ],
                  );
                },
                loading: () => const SizedBox.shrink(),
                error: (_, __) => const SizedBox.shrink(),
              );
            },
          ),
```

Add the provider import if not already present via `app_providers.dart` — check the top of the file: it already imports `import '../../providers/app_providers.dart';` (line 5), so no new import is needed for `ticketPrescriptionsProvider`.

- [ ] **Step 2: Verify the project still analyzes cleanly**

Run: `cd health_app && flutter analyze lib/screens/consultation/consultation_screen.dart`
Expected: `No issues found!`

- [ ] **Step 3: Commit**

```bash
cd health_app
git add lib/screens/consultation/consultation_screen.dart
git commit -m "feat: show prescriptions and add-prescription entry point in consultation detail"
```

---

### Task 11: PrescriptionsScreen and ProfileScreen entry point

**Files:**
- Create: `health_app/lib/screens/consultation/prescriptions_screen.dart`
- Modify: `health_app/lib/screens/profile/profile_screen.dart`

**Interfaces:**
- Consumes: `myPrescriptionsProvider` (Task 7), `PrescriptionCard` (Task 8), `ConsultationScreen` (existing), `ConsultationTicket` (existing model, for navigating back into a consult — see note in Step 1).

- [ ] **Step 1: Write the screen**

Navigating from a prescription back into its source `ConsultationScreen` needs a `ConsultationTicket`, but `/prescriptions/my` only returns `ticket_id`. Rather than fetching each ticket individually, tapping a card opens a minimal read-only detail view instead of the full `ConsultationScreen` — simplest option that needs no new backend call.

```dart
// health_app/lib/screens/consultation/prescriptions_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/app_providers.dart';
import '../../widgets/common_widgets.dart';
import '../../widgets/prescription_card.dart';

class PrescriptionsScreen extends ConsumerWidget {
  const PrescriptionsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prescriptionsAsync = ref.watch(myPrescriptionsProvider);

    return Scaffold(
      appBar: const CustomAppBar(title: 'My Prescriptions'),
      body: prescriptionsAsync.when(
        data: (prescriptions) {
          if (prescriptions.isEmpty) {
            return const EmptyState(
              title: 'No prescriptions yet',
              message: 'Prescriptions a doctor issues during a consultation will show up here.',
              icon: Icons.medication_outlined,
            );
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(myPrescriptionsProvider),
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: prescriptions.length,
              itemBuilder: (context, index) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: PrescriptionCard(prescription: prescriptions[index]),
              ),
            ),
          );
        },
        loading: () => const LoadingState(message: 'Loading your prescriptions...'),
        error: (e, _) => ErrorState(
          message: e.toString(),
          onRetry: () => ref.invalidate(myPrescriptionsProvider),
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Wire the entry point into ProfileScreen**

In `health_app/lib/screens/profile/profile_screen.dart`, add the import after the existing `app_providers.dart` import (currently line 5):

```dart
import '../consultation/prescriptions_screen.dart';
```

In `build`, after `final userAsync = ref.watch(userProvider);` (currently line 18), add:

```dart
    final isDoctor = authState.user?.role == 'doctor';
```

In the "Account" section, after the "Privacy & Security" tile (currently lines 142-147, right before `const SizedBox(height: 24),` on line 149), insert:

```dart
                  if (!isDoctor)
                    _SettingsTile(
                      title: 'My Prescriptions',
                      subtitle: 'View medications and care plans from your consults',
                      icon: Icons.medication_outlined,
                      onTap: () {
                        Navigator.of(context).push(
                          MaterialPageRoute(builder: (_) => const PrescriptionsScreen()),
                        );
                      },
                    ),
```

- [ ] **Step 3: Verify the project still analyzes cleanly**

Run: `cd health_app && flutter analyze lib/screens/consultation/prescriptions_screen.dart lib/screens/profile/profile_screen.dart`
Expected: `No issues found!`

- [ ] **Step 4: Commit**

```bash
cd health_app
git add lib/screens/consultation/prescriptions_screen.dart lib/screens/profile/profile_screen.dart
git commit -m "feat: add My Prescriptions screen and Profile entry point"
```

---

### Task 12: Full verification pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend test suite**

Run: `cd backend && python -m pytest -v`
Expected: PASS, zero failures, zero regressions in existing consultation/chat/auth tests

- [ ] **Step 2: Run the full Flutter test suite and analyzer**

Run: `cd health_app && flutter test && flutter analyze`
Expected: PASS, `No issues found!`

- [ ] **Step 3: Manual verification via the `run` skill**

Invoke the `run` skill to launch the app and backend together, then walk both flows end-to-end:
- **Doctor flow:** sign up/log in as a doctor, accept a pending consultation ticket (create one as a patient first if the queue is empty), open "Add Prescription", submit one medication plus a follow-up date, confirm it appears in the ticket's prescription list with an `ACTIVE` pill, then tap "Supersede with correction" and confirm the old entry flips to a `SUPERSEDED` pill while a new `ACTIVE` one appears.
- **Patient flow:** as the patient on that same ticket, open the consultation and confirm both prescriptions are visible (read-only, no supersede button); then go to Profile → "My Prescriptions" and confirm the same two entries show up there, newest first.

Report back what was observed (screenshots if the `run` skill captures them) — this is the acceptance check for the whole plan.
