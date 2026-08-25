# LLM-Backed Health Chatbot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the rule-based intent-detection chatbot engine with an OpenAI API-backed conversational engine, while keeping the existing safety/escalation pipeline (crisis detection, risk scoring, auto-escalation to a doctor) completely unchanged.

**Architecture:** `backend/app/routes/chat.py`'s `/chat/` handler keeps its existing order of operations (rate limit → consent → `is_safe()` crisis check → reply generation → `evaluate_chat_risk()` escalation). Only the reply-generation step changes: a new `backend/ml/chatbot/llm_engine.py` builds a system prompt from a fixed persona plus the user's live health context, sends the last 10 turns of conversation history plus the new message to the OpenAI Chat Completions API, and returns the reply text. Any LLM failure is caught and replaced with a fixed fallback string so a down LLM can never block the (unchanged) risk-evaluation/escalation step that runs after it.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, `openai` Python SDK (Chat Completions API, model `gpt-4o-mini`).

## Global Constraints

- Do not modify `backend/ml/chatbot/safety.py` or `backend/app/services/escalation.py` — both are confirmed independent of reply text (see spec).
- Do not modify `backend/app/schemas/chat.py` (`ChatRequest`/`ChatResponse` shape is unchanged) or any frontend file — the API contract is unchanged.
- `ChatMessage.state` column stays in the model (no migration); it simply stops being written to.
- All new tests must mock the OpenAI call — no test may make a real network call to the OpenAI API.
- Reference spec: `docs/superpowers/specs/2026-07-24-llm-chatbot-design.md`.

---

### Task 1: Config and dependency for the OpenAI API client

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/test_config.py` (new)

**Interfaces:**
- Produces: `Settings.OPENAI_API_KEY: str`, `Settings.OPENAI_MODEL: str`, `Settings.CHAT_MAX_TOKENS: int` on the `Settings` class returned by `get_settings()` — consumed by Task 2's `llm_engine.py`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_config.py`:

```python
from app.config import get_settings


def test_openai_settings_have_expected_defaults(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("CHAT_MAX_TOKENS", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.OPENAI_API_KEY == ""
    assert settings.OPENAI_MODEL == "gpt-4o-mini"
    assert settings.CHAT_MAX_TOKENS == 512

    get_settings.cache_clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_config.py -v`
Expected: FAIL with `AttributeError: 'Settings' object has no attribute 'OPENAI_API_KEY'`

- [ ] **Step 3: Add the settings**

In `backend/app/config.py`, inside the `Settings` class, immediately after the existing `CHAT_RATE_WINDOW_SECONDS` line:

```python
    CHAT_RATE_WINDOW_SECONDS: int = int(os.getenv("CHAT_RATE_WINDOW_SECONDS", "60"))
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    CHAT_MAX_TOKENS: int = int(os.getenv("CHAT_MAX_TOKENS", "512"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Add the dependency and .env.example entries**

In `backend/requirements.txt`, add a new line after `sentry-sdk==2.17.0`:

```
openai==1.59.0
```

In `backend/.env.example`, add after `CHAT_RATE_WINDOW_SECONDS=60`:

```
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
CHAT_MAX_TOKENS=512
```

Install the dependency: `cd backend && pip install openai==1.59.0`

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/.env.example backend/requirements.txt backend/tests/test_config.py
git commit -m "feat: add OpenAI API settings for LLM chatbot"
```

---

### Task 2: `llm_engine.py` — OpenAI-backed reply generation

**Files:**
- Create: `backend/ml/chatbot/llm_engine.py`
- Test: `backend/tests/test_llm_engine.py` (new)

**Interfaces:**
- Consumes: `Settings.OPENAI_API_KEY/OPENAI_MODEL/CHAT_MAX_TOKENS` (Task 1); `get_health_context(db, user_email) -> dict` from `backend/ml/chatbot/health_context.py` (existing, unchanged); `ChatMessage` model (`.message: str`, `.response: str`) from `backend/app/models/chat.py` (existing, unchanged).
- Produces: `generate_reply(message: str, db: Session, user_email: str, history: list[ChatMessage]) -> str` — consumed by Task 3's `chat.py`. Also produces `FALLBACK_REPLY: str` and internal `_call_llm(messages: list[dict]) -> str` (the only function that touches the network — Task 3's tests and Task 4's autouse fixture monkeypatch this exact name). Note: unlike a "system as a separate parameter" API, OpenAI's Chat Completions takes the system prompt as the first element of `messages` (`{"role": "system", "content": ...}`), so `_call_llm` takes only `messages` (system prompt included) rather than separate `system`/`messages` arguments.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_llm_engine.py`:

```python
from ml.chatbot import llm_engine


def test_generate_reply_returns_llm_text(monkeypatch):
    monkeypatch.setattr(
        llm_engine, "_call_llm", lambda messages: "Here's some advice."
    )

    reply = llm_engine.generate_reply(
        "I feel tired lately", db=None, user_email="x@example.com", history=[]
    )

    assert reply == "Here's some advice."


def test_generate_reply_falls_back_on_llm_error(monkeypatch):
    def _raise(messages):
        raise RuntimeError("simulated API failure")

    monkeypatch.setattr(llm_engine, "_call_llm", _raise)

    reply = llm_engine.generate_reply(
        "I feel tired lately", db=None, user_email="x@example.com", history=[]
    )

    assert reply == llm_engine.FALLBACK_REPLY


def test_system_prompt_includes_health_context(monkeypatch):
    captured = {}

    def _capture(messages):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(llm_engine, "_call_llm", _capture)

    llm_engine.generate_reply(
        "I feel tired lately", db=None, user_email="x@example.com", history=[]
    )

    # get_health_context(db=None, ...) returns avg_sleep_hours=7 as its test fallback
    system_message = captured["messages"][0]
    assert system_message["role"] == "system"
    assert "7 hours/night" in system_message["content"]


def test_history_is_expanded_into_alternating_turns(monkeypatch):
    from app.models.chat import ChatMessage

    captured = {}

    def _capture(messages):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(llm_engine, "_call_llm", _capture)

    past = ChatMessage(message="Hi", response="Hello! How can I help?")
    llm_engine.generate_reply(
        "I feel tired lately", db=None, user_email="x@example.com", history=[past]
    )

    # messages[0] is the system prompt; the rest are the conversation turns
    assert captured["messages"][1:] == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello! How can I help?"},
        {"role": "user", "content": "I feel tired lately"},
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_llm_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ml.chatbot.llm_engine'`

- [ ] **Step 3: Write the implementation**

Create `backend/ml/chatbot/llm_engine.py`:

```python
import logging

import openai
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.chat import ChatMessage
from ml.chatbot.health_context import get_health_context

logger = logging.getLogger(__name__)

FALLBACK_REPLY = (
    "I'm having trouble responding right now — please try again in a moment."
)

SYSTEM_PROMPT_TEMPLATE = """You are Heallio's health information assistant. You are not a doctor.
- Never provide a diagnosis, prescribe medication, or give dosing instructions.
- Encourage the user to consult a licensed healthcare professional for anything serious or urgent.
- Be warm, concise, and practical about everyday health topics: sleep, diet, exercise, hydration, mental wellness, and preventive care.

Here is what you know about this user's recent health data (last 7 days):
- Average sleep: {avg_sleep_hours} hours/night ({sleep_days_tracked} nights tracked)
- Average calories: {avg_calories} kcal/day ({diet_days_tracked} days tracked)
"""

_client = None


def _get_client():
    global _client
    if _client is None:
        settings = get_settings()
        _client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def _call_llm(messages: list[dict]) -> str:
    settings = get_settings()
    client = _get_client()
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        max_tokens=settings.CHAT_MAX_TOKENS,
        messages=messages,
    )
    return response.choices[0].message.content


def _build_system_prompt(db: Session, user_email: str) -> str:
    context = get_health_context(db, user_email)
    return SYSTEM_PROMPT_TEMPLATE.format(
        avg_sleep_hours=context.get("avg_sleep_hours", 0),
        sleep_days_tracked=context.get("sleep_days_tracked", 0),
        avg_calories=context.get("avg_calories", 0),
        diet_days_tracked=context.get("diet_days_tracked", 0),
    )


def _build_messages(
    system: str, history: list[ChatMessage], message: str
) -> list[dict]:
    turns = [{"role": "system", "content": system}]
    for entry in history:
        turns.append({"role": "user", "content": entry.message})
        turns.append({"role": "assistant", "content": entry.response})
    turns.append({"role": "user", "content": message})
    return turns


def generate_reply(
    message: str, db: Session, user_email: str, history: list[ChatMessage]
) -> str:
    try:
        system = _build_system_prompt(db, user_email)
        messages = _build_messages(system, history, message)
        return _call_llm(messages)
    except Exception:
        logger.exception("LLM chat call failed for user %s", user_email)
        return FALLBACK_REPLY
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_llm_engine.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/ml/chatbot/llm_engine.py backend/tests/test_llm_engine.py
git commit -m "feat: add OpenAI-backed llm_engine for chatbot replies"
```

---

### Task 3: Wire `chat.py` route to the new engine

**Files:**
- Modify: `backend/app/routes/chat.py:1-90`
- Modify: `backend/tests/conftest.py`
- Test: `backend/tests/test_chat_llm.py` (new)

**Interfaces:**
- Consumes: `generate_reply(message, db, user_email, history) -> str` and `_call_llm` from Task 2's `ml/chatbot/llm_engine.py`.

- [ ] **Step 1: Add an autouse test fixture that mocks the LLM call**

In `backend/tests/conftest.py`, add after the existing `_reset_rate_limiter` fixture:

```python
@pytest.fixture(autouse=True)
def _mock_llm_engine(monkeypatch):
    """Every test that hits /chat/ must not make a real network call to OpenAI."""
    from ml.chatbot import llm_engine

    monkeypatch.setattr(
        llm_engine,
        "_call_llm",
        lambda messages: "This is a mocked assistant reply for testing.",
    )
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_chat_llm.py`:

```python
def _signup_and_login(client, email: str, password: str):
    client.post(
        "/users/signup",
        json={"name": "Chat LLM User", "email": email, "password": password},
    )
    login = client.post(
        "/users/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return login.json()["access_token"]


def _grant_consent(client, token: str):
    consent = client.post(
        "/privacy/consent",
        json={"consent_given": True, "consent_version": "v1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert consent.status_code == 200


def test_chat_returns_mocked_llm_reply(client, random_email):
    token = _signup_and_login(client, random_email, "StrongPass1!")
    _grant_consent(client, token)

    response = client.post(
        "/chat/",
        json={"message": "I went for a walk today and feel fine"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["response"] == "This is a mocked assistant reply for testing."


def test_chat_passes_prior_turn_as_history(client, random_email, monkeypatch):
    from ml.chatbot import llm_engine

    token = _signup_and_login(client, random_email, "StrongPass1!")
    _grant_consent(client, token)

    client.post(
        "/chat/",
        json={"message": "first message"},
        headers={"Authorization": f"Bearer {token}"},
    )

    captured = {}

    def _capture(messages):
        captured["messages"] = messages
        return "second reply"

    monkeypatch.setattr(llm_engine, "_call_llm", _capture)

    response = client.post(
        "/chat/",
        json={"message": "second message"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert captured["messages"][0]["role"] == "system"
    assert captured["messages"][1] == {"role": "user", "content": "first message"}
    assert captured["messages"][-1] == {"role": "user", "content": "second message"}
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_chat_llm.py -v`
Expected: FAIL — `test_chat_returns_mocked_llm_reply` fails because the current handler still calls `chatbot_reply`, whose canned response won't match the mocked text.

- [ ] **Step 4: Update the route implementation**

**Correction (found in Task 3's task review, applied as a fix after initial implementation):** the original version of this step only swapped the reply-generation call and missed that `is_safe()`/`get_safety_message()` (from `ml/chatbot/safety.py`) used to run *inside* the old `chatbot_reply`, gating whether the LLM/rule-engine was even consulted. Since `chatbot_reply` is being replaced, `chat.py` must now call `is_safe()` itself, or crisis/dangerous-medical messages would reach the LLM with no deterministic intercept. `evaluate_chat_risk()` (further down, unchanged) still runs regardless — the original code never skipped it based on `is_safe`, so that part of the flow is unaffected.

In `backend/app/routes/chat.py`, change the import on line 7:

```python
from ml.chatbot.llm_engine import generate_reply
from ml.chatbot.safety import is_safe, get_safety_message
```

(remove `from ml.chatbot.chatbot_engine import chatbot_reply`)

Then replace this block (originally lines 67-90):

```python
        # Get last chat message to retrieve conversation state
        last_chat = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == user.id)
            .order_by(ChatMessage.id.desc())
            .first()
        )

        state = last_chat.state if last_chat else None

        # Get chatbot response
        reply, new_state = chatbot_reply(request.message, db, current_user_email, state)

        # Save chat message and response
        chat_entry = ChatMessage(
            user_id=user.id,
            message=request.message,
            response=reply,
            state=new_state,
        )
```

with:

```python
        # Load recent conversation history for the LLM's context
        history = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == user.id)
            .order_by(ChatMessage.id.desc())
            .limit(10)
            .all()
        )
        history.reverse()

        # Get chatbot response
        if is_safe(request.message):
            reply = generate_reply(request.message, db, current_user_email, history)
        else:
            reply = get_safety_message(request.message)

        # Save chat message and response
        chat_entry = ChatMessage(
            user_id=user.id,
            message=request.message,
            response=reply,
        )
```

Add a test to `backend/tests/test_chat_llm.py` covering the unsafe path:

```python
def test_chat_crisis_message_bypasses_llm(client, random_email):
    token = _signup_and_login(client, random_email, "StrongPass1!")
    _grant_consent(client, token)

    response = client.post(
        "/chat/",
        json={"message": "I want to kill myself"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "crisis helpline" in body["response"].lower() or "emergency" in body["response"].lower()
    assert body["response"] != "This is a mocked assistant reply for testing."
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_chat_llm.py tests/test_chat_escalation.py -v`
Expected: PASS (all tests in both files)

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/chat.py backend/tests/conftest.py backend/tests/test_chat_llm.py
git commit -m "feat: wire /chat/ route to OpenAI-backed llm_engine"
```

---

### Task 4: Remove the rule-based engine and its training artifacts

**Files:**
- Delete: `backend/ml/chatbot/chatbot_engine.py`
- Delete: `backend/ml/chatbot/intent_detector.py`
- Delete: `backend/ml/chatbot/symptom_checker.py`
- Delete: `backend/ml/chatbot/responses.py`
- Delete: `backend/ml/chatbot/train_intent_model.py`
- Delete: `backend/ml/chatbot/evaluate_intent_model.py`
- Delete: `backend/ml/chatbot/data/intent_dataset.json`
- Delete: `backend/ml/chatbot/model/intent_model.json`
- Delete: `backend/ml/chatbot/model/intent_training_report.json`
- Delete: `backend/ml/chatbot/model/intent_evaluation_report.json`

**Interfaces:**
- None produced or consumed — this task only removes code now superseded by Task 2/3. `ml/chatbot/health_context.py` and `ml/chatbot/safety.py` are not touched.

- [ ] **Step 1: Confirm nothing else references the files being deleted**

Run: `cd backend && grep -rn "chatbot_engine\|intent_detector\|symptom_checker\|from ml.chatbot.responses\|from ml.chatbot import responses" app/ ml/ --include=*.py`
Expected: no output (Task 3 already removed the only reference, in `app/routes/chat.py`)

- [ ] **Step 2: Delete the files**

```bash
git rm backend/ml/chatbot/chatbot_engine.py
git rm backend/ml/chatbot/intent_detector.py
git rm backend/ml/chatbot/symptom_checker.py
git rm backend/ml/chatbot/responses.py
git rm backend/ml/chatbot/train_intent_model.py
git rm backend/ml/chatbot/evaluate_intent_model.py
git rm backend/ml/chatbot/data/intent_dataset.json
git rm backend/ml/chatbot/model/intent_model.json
git rm backend/ml/chatbot/model/intent_training_report.json
git rm backend/ml/chatbot/model/intent_evaluation_report.json
```

- [ ] **Step 3: Run the full backend test suite**

Run: `cd backend && pytest -v`
Expected: PASS, 0 failures (no test imports any of the deleted modules)

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: remove superseded rule-based chatbot engine and intent-model artifacts"
```

---

## Self-Review Notes

- **Spec coverage:** Config/dependency (Task 1) → spec's Config section. `llm_engine.py` with prompt/history/fallback (Task 2) → spec's Components/Data flow/Error handling sections. Route wiring + history query + dropping `state` writes (Task 3) → spec's `chat.py` and `ChatMessage.state` sections. Deletions (Task 4) → spec's Deleted section (plus the training scripts/artifacts, which the spec didn't call out by name but which become dead code referencing a deleted module once `intent_detector.py` is gone — confirmed via grep that nothing in `app/` or the rest of `ml/` imports them).
- **Placeholder scan:** No TBD/TODO markers; every step has runnable code and an exact expected test outcome.
- **Type consistency:** `generate_reply(message: str, db: Session, user_email: str, history: list[ChatMessage]) -> str` matches its definition in Task 2 and its call site in Task 3. `_call_llm(messages: list[dict]) -> str` is the single name monkeypatched by Task 2's tests, Task 3's fixture, and Task 3's own test — consistent throughout (revised from the two-argument `_call_llm(system, messages)` shape used in the Claude-based draft, since OpenAI's Chat Completions API takes the system prompt as a `messages` entry rather than a separate parameter).
