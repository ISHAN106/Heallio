# Heallio

Heallio is an AI-assisted health companion platform. Patients track their
vitals, chat with an AI health assistant, get flagged for a doctor visit when
something looks risky, and message a real doctor in real time. Doctors get a
dashboard to manage their queue, chat with patients, and issue prescriptions.

The project is a monorepo: a FastAPI backend backed by PostgreSQL, and a
Flutter frontend that serves both the patient and doctor experience from one
codebase (role-based navigation after login).

## What it does

**For patients**

- Track daily health metrics: heart rate, sleep, steps, calories, blood
  pressure, blood glucose
- Chat with an LLM-backed health assistant that has context on your recent
  tracked data (sleep/diet averages) and gives general wellness guidance —
  never a diagnosis or prescription
- Automatic risk detection on chat messages and tracked stats: dangerous
  patterns (e.g. an extreme heart rate, severe symptoms described in chat, an
  extreme glucose or blood-pressure reading) escalate straight to a
  consultation ticket with a doctor; moderate risk shows an inline
  "consult a doctor?" suggestion you can accept or dismiss
- Real-time chat with an assigned doctor over WebSocket once a consultation
  is open, with reconnect handling if the connection drops
- View prescriptions doctors have issued, including superseded/updated ones
- Food scan and body scan: snap a photo, get a CNN-based analysis
- Weekly insights generated from tracked data
- Manage connected sessions/devices and revoke access to any one of them
  individually, independent of a full logout

**For doctors**

- A dashboard with today's stats (active cases, average response time,
  prescriptions issued, rating) and clinical specialty tags
- A queue of pending and assigned consultations, sorted by severity
- Accept a ticket, chat with the patient live, close the consultation, and
  get rated afterward
- Issue and supersede prescriptions tied to a consultation

## Architecture

```
Heallio/
├── backend/            FastAPI + PostgreSQL API
│   ├── app/
│   │   ├── routes/     REST endpoints (auth, health, diet, sleep, insights,
│   │   │               chat, privacy, scan, doctors, consultations,
│   │   │               prescriptions) + the consultation WebSocket
│   │   ├── services/   auth/session/token logic, rate limiting, account
│   │   │               lockout, risk escalation, audit logging, scheduler
│   │   ├── models/     SQLAlchemy models
│   │   └── schemas/    Pydantic request/response schemas
│   ├── ml/
│   │   ├── chatbot/    LLM prompt building + safety/crisis-phrase gating
│   │   ├── food_scan/  food-image CNN (training + inference)
│   │   └── body_scan/  body-image CNN (training + inference)
│   ├── alembic/        DB migrations
│   └── tests/          pytest suite (auth, config, health endpoints, ...)
├── health_app/          Flutter app (patient + doctor UI)
│   └── lib/
│       ├── screens/     auth, home, chat, consultation, health, insights,
│       │                scan, profile, doctor dashboard
│       ├── widgets/      shared UI (status pills, cards, bottom nav, ...)
│       ├── services/     API client (REST + WebSocket)
│       ├── providers/    Riverpod state (auth, chat, consultations, ...)
│       └── models/       Dart data models mirroring the backend schemas
└── docs/                design references and screen mockups
```

## Tech stack

- **Backend**: FastAPI, SQLAlchemy, Alembic, PostgreSQL, JWT auth (access +
  refresh tokens with per-device session tracking and revocation), APScheduler
  for background cleanup, Groq (OpenAI-compatible API) for the LLM chatbot,
  PyTorch/torchvision for the food/body scan CNNs
- **Frontend**: Flutter, Riverpod for state management, `web_socket_channel`
  for live consultation chat, Google Fonts (Geist)
- **Auth & security**: bcrypt password hashing, rate limiting on login/chat,
  account lockout after repeated failed logins, audit logging, privacy
  consent gating before chat access, per-session revocation independent of
  global logout

## Getting started

### Backend

```
cd backend
python -m venv venv && source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, SECRET_KEY, GROQ_API_KEY, etc.
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

See `backend/README.md` for details on connecting to PostgreSQL, running
tests (`pytest -q`), and the privacy/consent endpoints.

### Frontend

```
cd health_app
flutter pub get
flutter run                 # or: flutter build web
```

By default the app points at `http://localhost:8000` / `http://127.0.0.1:8000`
depending on platform — adjust `health_app/lib/config/app_config.dart` if
your backend runs elsewhere.

## Notes

- Training datasets and model checkpoints for the food/body scan CNNs are
  intentionally excluded from git (see `backend/.gitignore`) — regenerate
  them locally via `train_cnn.py` in the respective `ml/food_scan/` or
  `ml/body_scan/` directory.
- Chat responses are informational only — the assistant is explicitly
  instructed never to diagnose, prescribe, or give dosing guidance, and
  always defers serious or urgent concerns to a licensed professional or an
  auto-escalated consultation.
