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
