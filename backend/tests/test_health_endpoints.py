def _signup_and_login(client, email: str, password: str):
    client.post(
        "/users/signup",
        json={"name": "Health User", "email": email, "password": password},
    )
    login = client.post(
        "/users/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    body = login.json()
    return body["access_token"], body.get("refresh_token")


def test_liveness_and_readiness(client):
    live = client.get("/health/live")
    ready = client.get("/health/ready")

    assert live.status_code == 200
    assert live.json()["status"] == "alive"

    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_protected_chat_requires_token(client):
    response = client.post("/chat/", json={"message": "hello"})
    assert response.status_code == 401


def test_chat_with_token(client, random_email):
    token, _ = _signup_and_login(client, random_email, "StrongPass1!")

    denied = client.post(
        "/chat/",
        json={"message": "hello"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert denied.status_code == 403

    consent = client.post(
        "/privacy/consent",
        json={"consent_given": True, "consent_version": "v1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert consent.status_code == 200

    response = client.post(
        "/chat/",
        json={"message": "hello"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "response" in response.json()


def test_privacy_delete_request_flow(client, random_email):
    token, _ = _signup_and_login(client, random_email, "StrongPass1!")

    consent = client.post(
        "/privacy/consent",
        json={"consent_given": True, "consent_version": "v1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert consent.status_code == 200

    delete_req = client.post(
        "/privacy/delete-request",
        json={"reason": "User requested account removal"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_req.status_code == 200
    payload = delete_req.json()
    assert payload["status"] == "pending"
