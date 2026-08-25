# Heallio - System Status

## Architecture Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                      Flutter App (health_app/lib)                  │
│  Screens: Auth (patient/doctor), Home, Chat, Health, Body Scan,    │
│           Insights, Profile, Doctor Console, Consultation Chat     │
│  Providers: Riverpod state management                              │
│  Widgets: Reusable UI components                                   │
│  Theme: Material Design 3 with custom colors                       │
└───────────────────────────────────────────────────────────────────┘
                             │
                (HTTP + JWT Token, WebSocket for live consultations)
                             │
┌───────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (backend/app)                   │
│  Routes: Users, Health, Diet, Sleep, Insights, Chat, Privacy,       │
│          Scan (food + body), Doctors, Consultations                │
│  Models: SQLAlchemy ORM (user, doctor, consultation, chat, health,  │
│          diet, sleep, privacy, token_revocation, audit_log, ...)   │
│  Services: JWT, rate limiting, account lockout, token blocklist,   │
│            audit, escalation, consultation WebSocket, scheduler    │
│  ML: chatbot intent/symptom engine, food-scan + body-scan models   │
│        │                    │                    │                 │
│    PostgreSQL           APScheduler         Prometheus             │
│    (Production)         (Background          (Metrics)            │
│    SQLite (Dev)           Jobs)                                    │
└───────────────────────────────────────────────────────────────────┘
```

## API Endpoints (by router prefix)

- **`/users`** — signup, login, refresh, logout, me
- **`/health`** — score, list records, log record
- **`/diet`** — log, my-records, categories
- **`/sleep`** — log, my-records, summary
- **`/insights`** — weekly, queue-refresh
- **`/chat`** — send message, history
- **`/privacy`** — consent, consent/me, delete-request
- **`/scan`** — analyze (body), food/analyze
- **`/doctors`** — me/profile, me/availability, available, {doctor_id}/reputation
- **`/consultations`** — manual, my, queue, {ticket_id}/accept, {ticket_id}/messages (get/post), {ticket_id}/close, {ticket_id}/rate

Plus `GET /health/live`, `GET /health/ready`, `GET /metrics` for health checks and monitoring.

## Project Structure

```
Heallio/
├── backend/                          # FastAPI application
│   ├── app/
│   │   ├── main.py                  # Entry point with middleware
│   │   ├── config.py                # Configuration
│   │   ├── database.py              # SQLAlchemy setup
│   │   ├── models/                  # Database models
│   │   ├── routes/                  # API endpoints
│   │   ├── schemas/                 # Pydantic schemas
│   │   ├── services/                # Business logic (auth, ws, scheduler...)
│   │   └── ml/                      # chatbot/ and food_scan/ ML engines
│   ├── alembic/                     # Database migrations
│   ├── tests/                       # Test suite
│   ├── requirements.txt             # Python dependencies
│   └── docker-compose.yml           # Container orchestration
│
├── health_app/                       # Flutter application (patient + doctor)
│   ├── lib/
│   │   ├── main.dart                # App entry point, role-based routing
│   │   ├── theme/                   # Design system
│   │   ├── models/                  # Data models
│   │   ├── services/                # API client / auth store
│   │   ├── providers/               # Riverpod state
│   │   ├── widgets/                 # Reusable components
│   │   ├── screens/
│   │   │   ├── auth/                # auth choice, patient auth, doctor auth
│   │   │   ├── home/, chat/, health/, scan/, insights/, profile/
│   │   │   ├── doctor/               # doctor navigation/console
│   │   │   └── consultation/         # live consultation chat
│   │   └── config/                  # App configuration
│   └── pubspec.yaml
│
└── docs/                             # Design specs and documentation
```

## Technology Stack

**Backend:** FastAPI, SQLAlchemy, SQLite (dev) / PostgreSQL (prod), Alembic, JWT auth, APScheduler, Prometheus, Pytest, Docker.

**Frontend:** Flutter, Riverpod, Material Design 3.

## Security & Privacy

- JWT access/refresh tokens, password hashing, token revocation on logout, account lockout after repeated failures
- Consent required before AI chat use, data-deletion request workflow
- Request-ID tracing, rate limiting, CORS restricted to configured origins, production safety checks in `config.py`

## Known Gaps

- Automated test coverage (`backend/tests/`) currently covers auth and health endpoints only — doctors, consultations, scan, and chat routes are untested.
- `docs/` folder is used for design specs going forward (see `docs/superpowers/specs/`).

For setup steps, see [QUICK_START.md](./QUICK_START.md) and [SETUP_AND_RUN.md](./SETUP_AND_RUN.md).
