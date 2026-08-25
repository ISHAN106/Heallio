from types import SimpleNamespace

from ml.chatbot import llm_engine
from ml.chatbot.llm_engine import _call_llm


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


def test_call_llm_falls_back_when_openai_returns_none_content(monkeypatch):
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(
                    choices=[
                        SimpleNamespace(message=SimpleNamespace(content=None))
                    ]
                )
            )
        )
    )

    monkeypatch.setattr(llm_engine, "_get_client", lambda: fake_client)

    result = _call_llm([{"role": "user", "content": "test"}])

    assert result == llm_engine.FALLBACK_REPLY
