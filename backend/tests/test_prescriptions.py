from app.database import SessionLocal
from app.models.consultation import ConsultationTicket
from app.models.user import User


def _signup_and_login(client, email: str, password: str, role: str = "user"):
    client.post(
        "/users/signup",
        json={"name": f"{role.title()} User", "email": email, "password": password, "role": role},
    )
    login = client.post(
        "/users/login",
        data={"username": email, "password": password, "role": role},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return login.json()["access_token"]


def _grant_consent(client, token: str):
    client.post(
        "/privacy/consent",
        json={"consent_given": True, "consent_version": "v1"},
        headers={"Authorization": f"Bearer {token}"},
    )


def _create_accepted_ticket(client, patient_email, doctor_email):
    patient_token = _signup_and_login(client, patient_email, "StrongPass1!", "user")
    _grant_consent(client, patient_token)
    doctor_token = _signup_and_login(client, doctor_email, "StrongPass1!", "doctor")

    ticket = client.post(
        "/consultations/manual",
        json={"reason": "Persistent headache", "category_name": "General Physician"},
        headers={"Authorization": f"Bearer {patient_token}"},
    ).json()

    client.post(
        f"/consultations/{ticket['id']}/accept",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )

    # The escalation service auto-assigns the "best available" doctor to a new
    # ticket, falling back to *any* available doctor when the requested
    # category has no seeded DoctorCategory row (true in the test DB, which is
    # built via Base.metadata.create_all and never runs the Alembic seed
    # migration). That can silently hand the ticket to a doctor left over from
    # an earlier test, making the /accept call above a no-op (409). Force the
    # ticket onto this test's own doctor so downstream assertions are
    # deterministic regardless of auto-assignment or test execution order.
    db = SessionLocal()
    try:
        doctor = db.query(User).filter(User.email == doctor_email).first()
        db_ticket = db.query(ConsultationTicket).filter(ConsultationTicket.id == ticket["id"]).first()
        db_ticket.doctor_id = doctor.id
        db_ticket.status = "accepted"
        db.commit()
    finally:
        db.close()

    return ticket["id"], patient_token, doctor_token


def test_doctor_can_create_prescription(client, random_email):
    ticket_id, patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )

    response = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={
            "items": [{"medication_name": "Paracetamol", "dosage": "500mg", "frequency": "twice daily"}],
            "notes": "Drink plenty of fluids",
            "follow_up_date": "2026-07-20",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "active"
    assert body["notes"] == "Drink plenty of fluids"
    assert len(body["items"]) == 1
    assert body["items"][0]["medication_name"] == "Paracetamol"


def test_patient_cannot_create_prescription(client, random_email):
    ticket_id, patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )

    response = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Self-prescribing", "follow_up_date": None},
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert response.status_code == 403


def test_unassigned_doctor_cannot_create_prescription(client, random_email):
    ticket_id, _patient_token, _doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    other_doctor_token = _signup_and_login(client, f"other-doctor-{random_email}", "StrongPass1!", "doctor")

    response = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Not my patient", "follow_up_date": None},
        headers={"Authorization": f"Bearer {other_doctor_token}"},
    )
    assert response.status_code == 403


def test_cannot_create_prescription_on_pending_ticket(client, random_email):
    patient_token = _signup_and_login(client, f"patient-{random_email}", "StrongPass1!", "user")
    _grant_consent(client, patient_token)
    doctor_token = _signup_and_login(client, f"doctor-{random_email}", "StrongPass1!", "doctor")

    ticket = client.post(
        "/consultations/manual",
        json={"reason": "Persistent headache", "category_name": "General Physician"},
        headers={"Authorization": f"Bearer {patient_token}"},
    ).json()

    # See the note in _create_accepted_ticket: the escalation service may
    # auto-assign a leftover doctor from an earlier test to this new ticket.
    # Force it back to a genuinely unassigned/pending state so this test
    # verifies the "pending ticket" rule rather than an unrelated doctor's
    # auto-assignment outcome.
    db = SessionLocal()
    try:
        db_ticket = db.query(ConsultationTicket).filter(ConsultationTicket.id == ticket["id"]).first()
        db_ticket.doctor_id = None
        db_ticket.status = "pending"
        db.commit()
    finally:
        db.close()

    # A pending ticket always has no assigned doctor (see escalation.py), so
    # any doctor calling this is necessarily not the assigned doctor — the
    # ownership check fires first (403), which is checked before ticket
    # status precisely so a doctor with no relationship to a ticket can't
    # learn its status via the response code.
    response = client.post(
        f"/consultations/{ticket['id']}/prescriptions",
        json={"items": [], "notes": "No doctor assigned yet", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 403


def test_cannot_create_prescription_on_closed_ticket(client, random_email):
    ticket_id, patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    client.post(f"/consultations/{ticket_id}/close", headers={"Authorization": f"Bearer {doctor_token}"})

    response = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Too late", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 400


def test_empty_submission_rejected(client, random_email):
    ticket_id, _patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )

    response = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": None, "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 422


def test_ticket_prescriptions_visible_to_patient_and_doctor(client, random_email):
    ticket_id, patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Rest", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )

    for token in (patient_token, doctor_token):
        response = client.get(
            f"/consultations/{ticket_id}/prescriptions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert len(response.json()) == 1


def test_ticket_prescriptions_hidden_from_non_participant(client, random_email):
    ticket_id, _patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Rest", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    outsider_token = _signup_and_login(client, f"outsider-{random_email}", "StrongPass1!", "user")

    response = client.get(
        f"/consultations/{ticket_id}/prescriptions",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert response.status_code == 403


def test_my_prescriptions_lists_doctor_name(client, random_email):
    ticket_id, patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Rest", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )

    response = client.get(
        "/prescriptions/my",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["doctor_name"] == "Doctor User"
    assert body[0]["ticket_id"] == ticket_id


def test_doctor_can_supersede_prescription(client, random_email):
    ticket_id, patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    original = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={
            "items": [{"medication_name": "Paracetamol", "dosage": "500mg"}],
            "notes": None,
            "follow_up_date": None,
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    ).json()

    response = client.post(
        f"/prescriptions/{original['id']}/supersede",
        json={
            "items": [{"medication_name": "Paracetamol", "dosage": "1000mg"}],
            "notes": "Dosage increased",
            "follow_up_date": None,
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 201
    corrected = response.json()
    assert corrected["status"] == "active"
    assert corrected["supersedes_id"] == original["id"]
    assert corrected["items"][0]["dosage"] == "1000mg"

    ticket_prescriptions = client.get(
        f"/consultations/{ticket_id}/prescriptions",
        headers={"Authorization": f"Bearer {patient_token}"},
    ).json()
    statuses = {p["id"]: p["status"] for p in ticket_prescriptions}
    assert statuses[original["id"]] == "superseded"
    assert statuses[corrected["id"]] == "active"

    # The status flip above doesn't prove the OLD row's own content was left
    # untouched by the supersede call. Verify the original prescription's
    # items still hold the pre-supersede data (500mg), not the new dosage
    # (1000mg) submitted in the supersede POST — this would catch a bug that
    # mutated the old row's item in place instead of only writing a new row.
    old_prescription = next(p for p in ticket_prescriptions if p["id"] == original["id"])
    assert len(old_prescription["items"]) == 1
    assert old_prescription["items"][0]["medication_name"] == "Paracetamol"
    assert old_prescription["items"][0]["dosage"] == "500mg"
    assert old_prescription["items"][0]["dosage"] != corrected["items"][0]["dosage"]


def test_cannot_supersede_already_superseded_prescription(client, random_email):
    ticket_id, _patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    original = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Rest", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    ).json()
    client.post(
        f"/prescriptions/{original['id']}/supersede",
        json={"items": [], "notes": "Rest more", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )

    response = client.post(
        f"/prescriptions/{original['id']}/supersede",
        json={"items": [], "notes": "Again", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 400


def test_other_doctor_cannot_supersede(client, random_email):
    ticket_id, _patient_token, doctor_token = _create_accepted_ticket(
        client, f"patient-{random_email}", f"doctor-{random_email}"
    )
    original = client.post(
        f"/consultations/{ticket_id}/prescriptions",
        json={"items": [], "notes": "Rest", "follow_up_date": None},
        headers={"Authorization": f"Bearer {doctor_token}"},
    ).json()
    other_doctor_token = _signup_and_login(client, f"other-doctor-{random_email}", "StrongPass1!", "doctor")

    response = client.post(
        f"/prescriptions/{original['id']}/supersede",
        json={"items": [], "notes": "Not mine", "follow_up_date": None},
        headers={"Authorization": f"Bearer {other_doctor_token}"},
    )
    assert response.status_code == 403
