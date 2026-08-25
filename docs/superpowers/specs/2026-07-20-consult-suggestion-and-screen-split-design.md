# Consult Suggestions + Consultation/Chat Screen Split

Date: 2026-07-20

## Problem

Two related issues in the doctor-consultation flow:

1. **No patient autonomy in escalation.** `evaluate_chat_risk` (backend/app/services/escalation.py) buckets every chat message into `critical` / `high` / `medium` / `low`. Today, `should_escalate` is true for both `high` and `critical`, and the chat route (backend/app/routes/chat.py) auto-creates a consultation ticket the moment either bucket is hit — no confirmation from the patient. Patients find this invasive for anything short of a real emergency (e.g. persistent poor sleep, general anxiety talk landing in `high` due to context scoring).
2. **Consultation screen does two jobs.** `health_app/lib/screens/consultation/consultation_chat_screen.dart` (458 lines) combines ticket metadata + accept/close/rate actions + the live message thread + websocket handling in one widget, and it is only ever pushed from the doctor navigation flow — patients have no way to open their own ticket and chat with the doctor, even though the backend already allows it (`_ensure_access` permits `ticket.user_id` as well as `ticket.doctor_id`).

## Decision: what stays automatic

The hard-safety keyword paths in `evaluate_chat_risk` (`SELF_HARM_PHRASES`, `ACUTE_PHRASES`, and the `critical` entries in `RISK_KEYWORDS`: suicide, chest pain, unconscious, overdose, stroke) score `>= 90`, landing in `severity_level == "critical"`. **This path is explicitly out of scope** — auto-escalation for `critical` stays exactly as it is today. This was a deliberate, explicit call by the project owner: those cases will be revisited separately, and are not to be touched by this change.

Everything else — `high` (e.g. panic attack, can't breathe, very high BP, or context-derived scores like extreme sleep/calorie patterns) and `medium` (e.g. anxiety, dizziness, poor sleep trend) — changes from auto-escalate to **suggest, patient decides**.

```
severity_level == critical  -> auto-create ticket immediately (UNCHANGED)
severity_level == high      -> chatbot suggests a consult; patient accepts or dismisses (NEW)
severity_level == medium    -> chatbot suggests a consult; patient accepts or dismisses (NEW)
severity_level == low       -> no action (UNCHANGED)
```

## Part 1 — Backend: suggestion instead of auto-escalation

### `backend/app/services/escalation.py`

No changes to `evaluate_chat_risk`'s scoring logic. `should_escalate` continues to mean "critical only" for the purposes of *auto-creation* — the route (not the service) decides what to do with `high`/`medium`. Concretely:

- Rename nothing; keep `should_escalate = severity in {"high", "critical"}` as the general "this is risk-worthy" signal (used for the suggestion decision too), but the route splits behavior by exact `severity_level` instead of relying solely on `should_escalate`.

### `backend/app/routes/chat.py`

In the `/chat/` handler, after computing `risk`:

- If `risk["severity_level"] == "critical"`: unchanged — call `create_consultation_ticket` immediately, return `escalated=True` as today.
- Elif `risk["severity_level"] in {"high", "medium"}`: do **not** create a ticket. Return the reply plus a new `consultation_suggestion` object:
  ```json
  {
    "category_name": "Mental Health",
    "severity_level": "high",
    "reason": "Risk detected from chatbot conversation and recent health context."
  }
  ```
- Else (`low`): unchanged, plain response.

### `backend/app/schemas/chat.py`

Add to `ChatResponse`:
```python
consultation_suggestion: dict | None = None
```
(A lightweight inline dict is sufficient — this is not persisted, so a dedicated Pydantic model isn't needed. If preferred for type-safety, a small `ConsultationSuggestion` model with `category_name: str`, `severity_level: str`, `reason: str` is an equally valid, slightly more explicit alternative — implementer's choice.)

### Creating the ticket on acceptance

No new endpoint. The existing `POST /consultations/manual` (backend/app/routes/consultations.py, schema `ConsultationCreateManual { reason, category_name }`) already does exactly what's needed: patient-authenticated, creates via `create_consultation_ticket(trigger_source="manual", ...)`. The frontend calls this with the suggestion's `reason` and `category_name` when the patient taps "Consult a doctor."

### Persistence

The suggestion is ephemeral, attached only to the immediate `/chat/` response — it is **not** stored on the `ChatMessage` row and does not appear in `/chat/history`. This matches how `escalated`/`consultation_ticket_id` already behave today (history always returns `suggested_actions: []` and has no escalated field). If the user navigates away without acting on it, it's simply gone — same as a snackbar today.

## Part 2 — Frontend

### `health_app/lib/models/models.dart` — `ChatMessage`

Add:
```dart
final ConsultationSuggestion? consultationSuggestion;
```
New small class:
```dart
class ConsultationSuggestion {
  final String categoryName;
  final String severityLevel;
  final String reason;
  // fromJson parsing consultation_suggestion: {category_name, severity_level, reason}
}
```
Parsed in `ChatMessage.fromJson` from `json['consultation_suggestion']`, nullable.

### `health_app/lib/services/api_client.dart` — `sendMessage`

Pass through `data['consultation_suggestion']` into the map handed to `ChatMessage.fromJson`, same pattern as the existing `escalated`/`consultation_ticket_id` fields.

### `health_app/lib/screens/chat/chat_screen.dart`

- When the just-sent message's `consultationSuggestion` is non-null, render a small card beneath that bot response bubble (inline, not a snackbar): short text ("This sounds like something worth discussing with a doctor") + two buttons, `Consult a doctor` and `Not now`.
- `Not now` just hides the card via local widget state (per-message dismissed set) — no backend call.
- `Consult a doctor` calls `ApiClient` → `POST /consultations/manual` with `reason: suggestion.reason, category_name: suggestion.categoryName`, then navigates to `ConsultationScreen(ticket: created)` (see Part 2 below) via `Navigator.push`.
- This suggestion state is local/in-memory only (tied to the chat message list currently held by the provider), consistent with the "ephemeral" decision above — a screen reload won't resurrect a dismissed or unactioned suggestion.

### Screen split: `consultation_chat_screen.dart` → two screens

New/renamed files under `health_app/lib/screens/consultation/`:

1. **`consultation_screen.dart`** — `ConsultationScreen(ticket: ConsultationTicket)`
   - Owns: ticket state (`_ticket`), accept/close/rate logic and their loading flags, the header info block (trigger reason + severity/status/source pills), doctor-only accept button, close button, patient-only rating panel (shown when `status == closed && !isDoctor`).
   - New: an "Open Chat" button/tile that pushes `ConsultationThreadScreen(ticket: _ticket)`.
   - Replaces `ConsultationChatScreen` as the type pushed from `doctor_navigation_screen.dart` (both call sites).

2. **`consultation_thread_screen.dart`** — `ConsultationThreadScreen(ticket: ConsultationTicket)`
   - Owns: message list, history load (`ApiClient.getConsultationMessages`), websocket connect/subscribe/dispose (`ApiClient.consultationChannel`), send-message input bar, scroll-to-bottom behavior.
   - Pure messaging concern — no accept/close/rate logic, no ticket-status mutation.
   - Named `ConsultationThreadScreen` (not `ChatScreen`) to avoid collision with the existing AI-assistant `ChatScreen` in `screens/chat/chat_screen.dart`.

3. **`doctor_navigation_screen.dart`**: update its two `MaterialPageRoute(builder: (_) => ConsultationChatScreen(ticket: ticket))` pushes to `ConsultationScreen(ticket: ticket)`.

4. Old `consultation_chat_screen.dart` is deleted once the two new files replace its responsibilities.

### Patient access (new)

Nothing on the backend needs to change for patients to open their own ticket — `_ensure_access` already permits it. The gap was purely that no patient-facing UI ever pushed this screen. After this change, the "Consult a doctor" acceptance flow in `chat_screen.dart` is the first patient entry point into `ConsultationScreen`. (Whether patients also get a persistent "My Consultations" list entry point is a natural follow-up but is **not** part of this spec — out of scope, can be a fast follow.)

## Error handling

- `/consultations/manual` failure (network/4xx) on "Consult a doctor" tap: show a `SnackBar` with the error, keep the suggestion card visible so the patient can retry or dismiss.
- Existing error handling in the split screens (`ErrorState`, retry callbacks) carries over unchanged from the current combined screen — no behavior change, just relocated to the screen that owns the relevant state.

## Testing

- Backend: extend `evaluate_chat_risk`/route tests (or add if none exist) to assert:
  - a message scoring `critical` still auto-creates a ticket and returns `escalated=True`, no `consultation_suggestion`.
  - a message scoring `high` or `medium` does **not** create a ticket, returns `consultation_suggestion` with the right `category_name`/`severity_level`, and `escalated=False`.
  - a `low` message returns neither.
- Frontend: no existing automated widget tests for these screens (verified none exist today) — manual verification only, run via `flutter run`:
  - Trigger a medium-severity chat message as a patient, confirm the suggestion card renders under the bot bubble, confirm "Not now" dismisses it, confirm "Consult a doctor" creates a ticket and navigates into `ConsultationScreen` → `Open Chat` → `ConsultationThreadScreen` works end to end.
  - Doctor flow regression: confirm both `doctor_navigation_screen.dart` entry points still open `ConsultationScreen` correctly, accept/close/messaging still work post-split.

## Out of scope

- Any change to critical/hard-safety auto-escalation behavior (suicide/self-harm, chest pain, unconscious, overdose, stroke) — explicitly deferred by the project owner.
- A persistent "My Consultations" list screen for patients beyond the one created via a suggestion.
- Persisting suggestion state across reloads/chat history.
