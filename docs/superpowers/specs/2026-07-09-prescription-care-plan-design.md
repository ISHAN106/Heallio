# Prescription / Care-Plan Design

## Context

Heallio's consultation pipeline currently lets a patient open a ticket, get matched
with a doctor, chat over a WebSocket-backed thread, and close the ticket — at which
point the patient can leave a star rating. Nothing structured comes out of a
consult: no medication list, no care instructions, no record the patient can look
back on. This is the first of several planned additions to the patient/doctor
pipeline (notifications, appointment scheduling, and a doctor-side patient context
panel are separate, later specs); video consult and payment handling are explicitly
out of scope for the whole initiative.

This spec covers letting a doctor attach a structured prescription / care-plan to
an active consultation, and letting the patient see their prescription history.

## Goals

- A doctor can record medications (structured) and free-text care instructions
  against an active consultation, at any point while it's open (not just at close).
- A patient can see prescriptions inline in the consult they came from, and browse
  their full prescription history in one place.
- Once issued, a prescription's clinical content is never silently edited — a
  correction creates a new record that supersedes the old one.
- Issuing a prescription does not block or require closing the consult (optional,
  per the existing "close" flow).

## Non-goals

- Video consultation and payment/billing (excluded from this initiative entirely).
- Push/in-app notifications when a prescription is issued (separate spec; for now,
  visibility is via the open WebSocket thread and the patient checking the app).
- PDF export / printable prescriptions.
- Doctor-side "prescriptions I've written" history screen (doctors see prescriptions
  scoped to the ticket they're viewing; only the patient gets a cross-consult view).
- Appointment scheduling and the doctor patient-context panel (separate specs).

## Data model

New file `backend/app/models/prescription.py`, new Alembic migration.

```python
class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("consultation_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # patient, denormalized for `/prescriptions/my`

    notes = Column(Text, nullable=True)
    follow_up_date = Column(Date, nullable=True)
    status = Column(String, nullable=False, default="active")  # active | superseded
    supersedes_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("PrescriptionItem", cascade="all, delete-orphan", back_populates="prescription")


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

Immutability: there is no update endpoint for `Prescription` or `PrescriptionItem`
content. A correction is issued via the supersede action (below), which only ever
flips `status` on the old row — it never touches medication content.

Validation: a prescription must have at least one item OR non-empty `notes`. A
purely empty submission (no meds, no notes) is rejected at the Pydantic schema
level with a 422.

## Backend API

New router `backend/app/routes/prescriptions.py`, mounted alongside the existing
`consultations` router. Reuses `_ensure_access`-style checks and the existing
`write_audit_log` / `consultation_ws.manager` helpers already used by
`consultations.py`.

- `POST /consultations/{ticket_id}/prescriptions`
  Doctor-only (`require_role("doctor")`), and the doctor must be the ticket's
  assigned doctor. Ticket status must be `accepted` or `in_progress` — 400 if
  `pending` (no doctor assigned yet) or `closed`. Creates the `Prescription` +
  `PrescriptionItem` rows, writes an audit log entry
  (`event_type="prescription_created"`), and broadcasts
  `{"type": "system", "message": "prescription_added", "prescription_id": ...}`
  on the ticket's existing WebSocket channel so an open thread reflects it live.

- `GET /consultations/{ticket_id}/prescriptions`
  Patient or assigned doctor only (same access rule as consultation messages).
  Returns all prescriptions for the ticket, newest first, each with its items.

- `GET /prescriptions/my`
  Patient-only. Returns every prescription across all of the caller's consults,
  newest first, each entry including `doctor_name` and `ticket_id` for context.

- `POST /prescriptions/{id}/supersede`
  Doctor-only, and only the doctor who owns the prescription's ticket. 400 if the
  target prescription is already `superseded`. Body is the same shape as create
  (new items/notes/follow_up_date). Effect: sets the old row's `status` to
  `superseded`, creates a new `Prescription` with `supersedes_id` = old id,
  `status="active"`. Writes an audit log entry
  (`event_type="prescription_superseded"`) and broadcasts on the WS channel like
  create does.

### Schemas (`backend/app/schemas/prescription.py`)

```python
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

    # validator: at least one of items or notes must be non-empty

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

## Frontend (Flutter)

**Models** (`health_app/lib/models/models.dart`): `Prescription`, `PrescriptionItem`
mirroring the response schemas above, with `fromJson`.

**API client** (`health_app/lib/services/api_client.dart`): `createPrescription`,
`getTicketPrescriptions`, `getMyPrescriptions`, `supersedePrescription`.

**Doctor flow** (`ConsultationScreen`): a new card — "Add Prescription" — appears
when `currentUser.role == 'doctor'`, the doctor is the ticket's assigned doctor,
and `ticket.status` is `accepted` or `in_progress`. Tapping it pushes a new
`PrescriptionFormScreen`: a dynamically add/remove-able list of medication rows
(name/dosage/frequency/duration/instructions), a notes text area, and an optional
follow-up date picker (`showDatePicker`). Submitting posts and pops back.

Below that card, existing prescriptions for the ticket are listed (both roles see
this) using a shared `PrescriptionCard` widget: medication list, notes, follow-up
date, a `StatusPill` for `active`/`superseded`, and — doctor + active only — a
"Supersede" button that opens the same form pre-selected as a correction.

**Patient flow**: same `PrescriptionCard` list appears read-only in
`ConsultationScreen`. A new menu item "My Prescriptions" on `ProfileScreen` opens
a new `PrescriptionsScreen` (not a bottom-nav tab — the bar is already at 6 items)
listing every prescription across consults via `getMyPrescriptions`, each card
tappable to jump back into that consult's `ConsultationScreen`.

## Error handling

| Case | Response |
|---|---|
| Non-assigned doctor tries to create/supersede | 403 |
| Create on `pending`/`closed` ticket | 400 |
| Supersede an already-`superseded` prescription | 400 |
| Empty submission (no items, no notes) | 422 (schema validation) |
| Patient tries to create a prescription | 403 (`require_role("doctor")`) |
| Non-participant (not patient/doctor on ticket) reads prescriptions | 403 |

## Testing

- Backend: pytest cases mirroring the existing `consultations` route tests —
  create/list/supersede authorization boundaries, status-gating on ticket state,
  double-supersede rejection, empty-submission rejection.
- Frontend: manual verification via the `run` skill — walk both the doctor
  "add prescription" flow and the patient "view in thread + My Prescriptions"
  flow end-to-end against the running app.
