import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test_health.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000"
# Pin auth-throttling config so tests don't inherit a developer's local .env
# (load_dotenv() does not override values already set in the environment).
os.environ["MAX_FAILED_LOGIN_ATTEMPTS"] = "5"
os.environ["LOGIN_LOCKOUT_SECONDS"] = "300"
os.environ["LOGIN_RATE_LIMIT"] = "10"
os.environ["LOGIN_RATE_WINDOW_SECONDS"] = "60"

_TEST_DB_PATH = Path(__file__).resolve().parent.parent / "test_health.db"
if _TEST_DB_PATH.exists():
    _TEST_DB_PATH.unlink()


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The rate limiter is a process-wide singleton shared by the session-scoped
    `client` fixture. Without a reset, tests that make many requests from the
    same TestClient IP (e.g. a login-lockout test) trip the limiter for every
    test that runs after them in the same session."""
    from app.services.rate_limit import rate_limiter

    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture(autouse=True)
def _mock_llm_engine(monkeypatch):
    """Every test that hits /chat/ must not make a real network call to OpenAI."""
    from ml.chatbot import llm_engine

    monkeypatch.setattr(
        llm_engine,
        "_call_llm",
        lambda messages: "This is a mocked assistant reply for testing.",
    )


@pytest.fixture
def random_email() -> str:
    return f"test-{uuid.uuid4().hex[:10]}@example.com"
