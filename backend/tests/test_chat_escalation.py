from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.diet import DietRecord
from app.models.sleep import SleepRecord
from app.models.user import User


def _signup_and_login(client, email: str, password: str):
    client.post(
        "/users/signup",
        json={"name": "Chat Risk User", "email": email, "password": password},
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


def test_critical_message_still_auto_escalates(client, random_email):
    token = _signup_and_login(client, random_email, "StrongPass1!")
    _grant_consent(client, token)

    response = client.post(
        "/chat/",
        json={"message": "I have severe chest pain right now"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is True
    assert body["consultation_ticket_id"] is not None
    assert body["consultation_suggestion"] is None

    my_consultations = client.get(
        "/consultations/my",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert my_consultations.status_code == 200
    assert len(my_consultations.json()) == 1


def test_high_severity_message_suggests_instead_of_escalating(client, random_email):
    token = _signup_and_login(client, random_email, "StrongPass1!")
    _grant_consent(client, token)

    response = client.post(
        "/chat/",
        json={"message": "I think I'm having a panic attack"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is False
    assert body["consultation_ticket_id"] is None
    assert body["consultation_suggestion"] is not None
    assert body["consultation_suggestion"]["severity_level"] == "high"

    my_consultations = client.get(
        "/consultations/my",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert my_consultations.json() == []


def test_medium_severity_message_suggests_instead_of_escalating(client, random_email):
    token = _signup_and_login(client, random_email, "StrongPass1!")
    _grant_consent(client, token)

    response = client.post(
        "/chat/",
        json={"message": "I've been struggling with anxiety this week."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is False
    assert body["consultation_ticket_id"] is None
    assert body["consultation_suggestion"] is not None
    assert body["consultation_suggestion"]["severity_level"] == "medium"

    my_consultations = client.get(
        "/consultations/my",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert my_consultations.json() == []


def test_low_severity_message_has_no_suggestion(client, random_email):
    token = _signup_and_login(client, random_email, "StrongPass1!")
    _grant_consent(client, token)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == random_email).first()
        now = datetime.utcnow()
        db.add(
            SleepRecord(
                user_id=user.id,
                sleep_start=now - timedelta(hours=7),
                sleep_end=now,
                quality="good",
            )
        )
        db.add(
            DietRecord(
                user_id=user.id,
                meal_type="dinner",
                food="rice and vegetables",
                calories=2000,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/chat/",
        json={"message": "I went for a walk today and feel fine"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is False
    assert body["consultation_ticket_id"] is None
    assert body["consultation_suggestion"] is None
