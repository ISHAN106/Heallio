# LLM-Backed Health Chatbot (OpenAI API)

Date: 2026-07-24 (revised: switched provider from Anthropic Claude to OpenAI)

## Problem

The chatbot at `backend/ml/chatbot/chatbot_engine.py` is a fixed intent-detection tree: `intent_detector.py` classifies the message, `symptom_checker.py` runs a rigid multi-turn state machine, and `responses.py` returns canned template strings filled in with the user's health context. This caps conversation quality — it can't handle phrasing outside its keyword rules, can't hold a natural multi-turn conversation, and every new topic requires a new branch. The goal is to replace the conversational core with a real LLM (OpenAI) while keeping the safety-critical parts of the pipeline — crisis/unsafe-message detection and risk-based escalation to a doctor — exactly as they are today, since those are deterministic and auditable by design.

## Decision: what stays unchanged

`backend/app/routes/chat.py`'s `/chat/` handler keeps its existing shape and order of operations:

1. Rate limit check (unchanged)
2. Consent check (unchanged)
3. `is_safe(message)` / crisis check via `ml/chatbot/safety.py` — **correction:** in the pre-existing code this check lived *inside* `chatbot_engine.chatbot_reply`, not in `chat.py` itself; since `chatbot_reply` is being replaced, `chat.py` must now call `is_safe()` directly. When unsafe, the reply is `get_safety_message(message)` instead of calling the LLM — but `evaluate_chat_risk()` (step 5) still runs afterward exactly as it always has (the old code never skipped it either; it ran unconditionally after saving the chat message, regardless of `is_safe`'s result). An earlier draft of this spec incorrectly stated risk evaluation was skipped when unsafe — it is not.
4. **Reply generation (this spec replaces this step)** — LLM call only happens when `is_safe(message)` is true; otherwise the deterministic safety message is used as the reply
5. `evaluate_chat_risk()` via `app/services/escalation.py` (unchanged, always runs) — critical still auto-creates a consultation ticket; high/medium still returns a `consultation_suggestion`; low returns plain response

`safety.py` and `escalation.py` are not touched. Both operate on the raw user message / stored health data, not on the reply text, so they're unaffected by the engine swap (confirmed against `tests/test_chat_escalation.py`, which asserts only on `escalated`/`consultation_suggestion`/severity fields, never on reply content).

## Components

### New: `backend/ml/chatbot/llm_engine.py`

```python
def generate_reply(message: str, db: Session, user_email: str, history: list[ChatMessage]) -> str
```

- Owns a module-level OpenAI client instance (so tests can `monkeypatch` it).
- Builds a system prompt from:
  - A fixed persona/guardrail block: health-information assistant, not a doctor, no diagnosis, no prescriptions, no medication dosing; for anything urgent, defer to the existing safety messaging tone.
  - The user's live health context, reused as-is from `ml/chatbot/health_context.py` (`get_health_context(db, user_email)` — sleep/calorie/etc. averages).
- Builds the message list for the Chat Completions API from `history`: the last 10 `ChatMessage` rows (ordered oldest → newest), each expanded into a `user` turn (`.message`) followed by an `assistant` turn (`.response`), plus the new incoming `message` as the final `user` turn. The system prompt is prepended as a `system`-role message.
- Calls `client.chat.completions.create(model=settings.OPENAI_MODEL, max_tokens=settings.CHAT_MAX_TOKENS, messages=[{"role": "system", "content": system}, *turns])` and returns `response.choices[0].message.content`.
- Wraps the call in try/except: on any exception (timeout, rate limit, API error, missing key), logs it and returns a fixed fallback string: `"I'm having trouble responding right now — please try again in a moment."` Never raises — the caller's risk evaluation must still run against the user's raw message regardless of LLM availability.

### `backend/app/routes/chat.py`

Replace the call to `chatbot_reply(request.message, db, current_user_email, state)` with:

```python
history = (
    db.query(ChatMessage)
    .filter(ChatMessage.user_id == user.id)
    .order_by(ChatMessage.id.desc())
    .limit(10)
    .all()
)
history.reverse()

if is_safe(request.message):
    reply = generate_reply(request.message, db, current_user_email, history)
else:
    reply = get_safety_message(request.message)
```

`is_safe` and `get_safety_message` are imported from `ml.chatbot.safety` (unchanged module). Everything after this — saving `chat_entry`, calling `evaluate_chat_risk`, and the escalation branches — is unchanged and runs regardless of which branch produced `reply`.

The `state`/`new_state` plumbing (previously threading `symptom_checker` state through `ChatMessage.state`) is removed from this handler — `ChatMessage` is created with `state=None` going forward, since history is now reconstructed from the message rows themselves rather than a serialized state string.

### `backend/app/config.py`

Add:
```python
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
CHAT_MAX_TOKENS: int = int(os.getenv("CHAT_MAX_TOKENS", "512"))
```

### `backend/requirements.txt`

Add the `openai` package.

### Deleted

- `ml/chatbot/intent_detector.py`
- `ml/chatbot/symptom_checker.py`
- `ml/chatbot/responses.py`
- `ml/chatbot/chatbot_engine.py` (superseded by `llm_engine.py`)

`ml/chatbot/safety.py`, `ml/chatbot/health_context.py`, and `app/services/escalation.py` are kept as-is.

### `backend/app/models/chat.py` — `ChatMessage.state`

Column is left in place (no migration) — it simply stops being written to. Dropping it is a separate, unrelated concern.

## Data flow

```
POST /chat/ { message }
  -> rate limit, consent check (unchanged)
  -> load last 10 ChatMessage rows for this user
  -> is_safe(message)?
       no  -> reply = get_safety_message(message)  (LLM not called)
       yes -> reply = generate_reply(message, db, user_email, history)
                -> build system prompt (persona + health context)
                -> build turn list from history + new message
                -> call OpenAI Chat Completions API
                -> on success: return reply text
                -> on failure: return fallback string
  -> save new ChatMessage(message, reply, state=None)              [always runs]
  -> evaluate_chat_risk(db, user, message) (unchanged, always runs)
       -> critical: create ticket, escalated=True
       -> high/medium: consultation_suggestion
       -> low: plain response
```

## Error handling

- OpenAI API failure of any kind (timeout, 4xx/5xx, missing/invalid key) is caught inside `generate_reply` and converted to the fixed fallback string — the endpoint never 500s because of the LLM, and risk evaluation still runs on the user's raw message so a down LLM can't suppress an escalation.
- Missing `OPENAI_API_KEY` in a given environment behaves the same way (the OpenAI client raises on the call, caught by the same except block) rather than failing at startup — matches this codebase's existing pattern of env-driven optional features (e.g. `SENTRY_DSN`).

## Testing

- `llm_engine.py` gets unit tests with the module-level OpenAI client `monkeypatch`'d to a fake object whose `.chat.completions.create()` returns a canned response object — no real network calls or API key needed in CI.
  - Happy path: returned text matches the mocked response.
  - Fallback path: mock raises an exception, assert the fixed fallback string comes back.
  - Prompt construction: assert the user's health context (e.g. a known `avg_sleep_hours` value) appears in the constructed system prompt.
- `tests/test_chat_escalation.py` requires no changes — it already asserts only on `escalated`/`consultation_suggestion`/severity fields, never reply text, and will keep passing against the new engine as long as the OpenAI call is mocked in the test environment (add the same `monkeypatch` at the top of that test module, or a shared `conftest.py` fixture, so these tests don't make live API calls).

## Out of scope

- Frontend changes — `ChatResponse`'s shape (`response`, `escalated`, `consultation_ticket_id`, `consultation_suggestion`) is unchanged, so `health_app/lib/screens/chat/chat_screen.dart` and the API client need no changes.
- Streaming responses — this spec keeps the existing synchronous request/response shape.
- Removing `ChatMessage.state` column via migration.
- Any change to `safety.py` or `escalation.py` logic.
