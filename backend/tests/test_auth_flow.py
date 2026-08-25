from app.database import SessionLocal
from app.models.user import User


def test_signup_login_refresh_logout_flow(client, random_email):
    signup_payload = {
        "name": "Test User",
        "email": random_email,
        "password": "StrongPass1!",
    }

    signup = client.post("/users/signup", json=signup_payload)
    assert signup.status_code == 201

    login = client.post(
        "/users/login",
        data={"username": random_email, "password": "StrongPass1!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    login_json = login.json()
    assert "access_token" in login_json
    assert "refresh_token" in login_json

    refresh_token = login_json["refresh_token"]

    refresh = client.post("/users/refresh", json={"refresh_token": refresh_token})
    assert refresh.status_code == 200
    assert "access_token" in refresh.json()

    logout = client.post("/users/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 200

    refresh_after_logout = client.post(
        "/users/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_after_logout.status_code == 401


def test_login_unknown_email_is_rejected_without_creating_account(client, random_email):
    # Login must NOT silently create accounts; unknown emails fail like a bad
    # password and users must go through /users/signup.
    login = client.post(
        "/users/login",
        data={"username": random_email, "password": "StrongPass1!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 401

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == random_email).first()
        assert user is None
    finally:
        db.close()


def _signup_and_login(client, email):
    client.post(
        "/users/signup",
        json={"name": "Auth User", "email": email, "password": "StrongPass1!"},
    )
    login = client.post(
        "/users/login",
        data={"username": email, "password": "StrongPass1!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return login.json()


def test_access_token_is_revoked_after_logout(client, random_email):
    tokens = _signup_and_login(client, random_email)
    access, refresh = tokens["access_token"], tokens["refresh_token"]

    before = client.get("/users/me", headers={"Authorization": f"Bearer {access}"})
    assert before.status_code == 200

    logout = client.post("/users/logout", json={"refresh_token": refresh})
    assert logout.status_code == 200

    after = client.get("/users/me", headers={"Authorization": f"Bearer {access}"})
    assert after.status_code == 401


def test_refresh_token_cannot_authenticate_requests(client, random_email):
    tokens = _signup_and_login(client, random_email)
    refresh = tokens["refresh_token"]

    resp = client.get("/users/me", headers={"Authorization": f"Bearer {refresh}"})
    assert resp.status_code == 401


def test_doctor_login_requires_doctor_role(client, random_email):
    signup = client.post(
        "/users/signup",
        json={
            "name": "Doctor User",
            "email": random_email,
            "password": "StrongPass1!",
            "role": "doctor",
        },
    )
    assert signup.status_code == 201

    doctor_login = client.post(
        "/users/login",
        data={"username": random_email, "password": "StrongPass1!", "role": "doctor"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert doctor_login.status_code == 200
    assert doctor_login.json()["user"]["role"] == "doctor"

    patient_login = client.post(
        "/users/login",
        data={"username": random_email, "password": "StrongPass1!", "role": "user"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert patient_login.status_code == 403


def test_login_lockout_after_repeated_failures(client, random_email):
    client.post(
        "/users/signup",
        json={"name": "Locked User", "email": random_email, "password": "StrongPass1!"},
    )

    for _ in range(5):
        response = client.post(
            "/users/login",
            data={"username": random_email, "password": "WrongPass1!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code in (401, 423)

    locked = client.post(
        "/users/login",
        data={"username": random_email, "password": "StrongPass1!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert locked.status_code in (423, 429)
