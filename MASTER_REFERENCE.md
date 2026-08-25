# 📋 Master Reference Card

## 🎯 What You Have

```
Backend:   FastAPI + SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
Frontend:  Flutter + Riverpod + Material Design 3 — patient AND doctor experiences
API:       REST with JWT authentication, WebSocket for live consultations
Deploy:    Docker + GitHub Actions ready
```

---

## 🚀 START HERE

### Step 1: Backend
```bash
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload
```

### Step 2: Frontend
```bash
cd health_app
flutter run
```

### Step 3: Select Device
```
[d] Device  |  [a] Android  |  [i] iOS  |  [w] Web
```

App will build, connect to the backend, and show the auth-choice screen (Patient / Doctor).

---

## 🔗 Backend APIs (by router)

| Router | Purpose |
|---|---|
| `/users` | signup, login, refresh, logout, me |
| `/health` | health score, list/log records |
| `/diet` | log meals, my-records, categories |
| `/sleep` | log sleep, my-records, summary |
| `/insights` | weekly insights, queue-refresh |
| `/chat` | AI chatbot messages + history |
| `/privacy` | consent, delete-request |
| `/scan` | body-scan analysis, food-scan analysis |
| `/doctors` | doctor profile, availability, directory, reputation |
| `/consultations` | manual ticket, queue, accept, messages, close, rate |
| `/health/live`, `/health/ready`, `/metrics` | health checks + Prometheus |

### Frontend → Backend URL resolution
- Android emulator → `10.0.2.2:8000`
- iOS simulator / Web → `localhost:8000`
- Physical device → set your machine's IP, e.g. `flutter run --dart-define=API_BASE_URL=http://192.168.1.100:8000`

---

## 📱 App Screens (`health_app/lib/screens/`)

```
auth/          → auth choice, patient auth, doctor auth (login/signup)
home/          → patient dashboard
chat/          → AI health assistant
health/        → health/diet/sleep tracking
scan/          → body scan + food scan
insights/      → personalized recommendations
profile/       → account settings, privacy
doctor/        → doctor navigation (queue, patients, profile)
consultation/  → live patient-doctor consultation chat
```

Role after login (`AuthWrapper` in `main.dart`) determines whether the patient tab bar or the doctor console is shown.

---

## 🔐 Key Features

**Security** — JWT access/refresh tokens, automatic refresh, account lockout after repeated failures, secure password hashing, CORS restricted to configured origins.

**Privacy** — consent required before AI chat, data-deletion request workflow, audit logging.

**Data tracking** — steps/heart rate/calories, meals, sleep duration & quality, body scan and food scan via ML models.

**AI features** — health-aware chatbot with intent detection and symptom checking, personalized weekly insights.

**Doctor features** — doctor profiles & availability, consultation ticket queue, live chat consultations, reputation ratings.

**Monitoring** — request tracing, Prometheus metrics, structured error logging, background jobs via APScheduler.

---

## 💾 Database

SQLAlchemy models cover: users, doctors, consultations, chat, health, diet, sleep, privacy consent, token revocation, audit log, background tasks. Migrations are managed with Alembic.

```bash
cd backend
..\.venv\Scripts\python -m alembic current       # show current revision
..\.venv\Scripts\python -m alembic upgrade head   # apply all migrations
```

Development DB is SQLite and is git-ignored (recreated by running the app/tests) — do not commit `.db` files.

---

## 🛠️ Common Commands

```bash
# Backend
cd backend && ..\.venv\Scripts\python -m uvicorn app.main:app --reload
cd backend && ..\.venv\Scripts\python -m pytest -v
cd backend && ..\.venv\Scripts\python -m alembic upgrade head

# Frontend
cd health_app && flutter run
cd health_app && flutter clean && flutter pub get
cd health_app && flutter build apk --release
cd health_app && flutter build web --release
```

---

## 📚 Documentation

- **Quick Start:** `QUICK_START.md`
- **Full Setup:** `SETUP_AND_RUN.md`
- **System Overview:** `SYSTEM_STATUS.md`
- **UI Documentation:** `health_app/README_UI.md`
- **Backend Info:** `backend/README.md`
- **Design specs:** `docs/superpowers/specs/`

---

## 🆘 Troubleshooting

**Backend not responding**
```bash
curl http://localhost:8000/health/live
```

**App can't connect** — check `health_app/lib/config/app_config.dart` for the platform URL logic; physical devices need your machine's LAN IP.

**Flutter build errors**
```bash
cd health_app && flutter clean && flutter pub get && flutter run
```

**Database issues** — delete the local SQLite file (git-ignored) and rerun `alembic upgrade head`.
