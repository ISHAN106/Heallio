# 🚀 Quick Start Guide

## Run the App

### 1. Start the backend
```bash
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload
```
Runs on `http://localhost:8000`.

### 2. Start the Flutter app
```bash
cd health_app
flutter run
```
Select your target: **d** (device), **a** (Android emulator), **i** (iOS simulator), **w** (Web).

### 3. What you'll see
1. Auth-choice screen — pick **Patient** or **Doctor**
2. Sign up or log in
3. Patients land on the home dashboard; doctors land on the doctor console
4. Grant consent to unlock the AI chat assistant

---

## Quick Backend Checks

```bash
curl http://localhost:8000/health/live     # {"status":"alive"}
curl http://localhost:8000/health/ready    # {"status":"ready"}
curl http://localhost:8000/metrics         # Prometheus metrics
```

---

## Important Files

| File | Purpose |
|------|---------|
| `health_app/lib/main.dart` | App entry point, role-based routing (patient vs doctor) |
| `health_app/lib/services/api_client.dart` | Backend communication |
| `health_app/lib/config/app_config.dart` | Platform-aware backend URLs |
| `health_app/lib/theme/app_theme.dart` | Design system |
| `backend/app/main.py` | Backend entry point |
| `backend/app/config.py` | Backend config |
| `backend/requirements.txt` | Python dependencies |

---

## Key Features

✅ **Auth** — patient and doctor signup/login, JWT with automatic refresh
✅ **Health tracking** — steps, heart rate, calories, meals, sleep
✅ **Body & food scan** — ML-driven analysis from photos
✅ **AI chat** — consent-gated health assistant with intent detection
✅ **Insights** — weekly AI-generated recommendations
✅ **Doctor console** — availability, consultation queue, live chat with patients, reputation
✅ **Privacy** — consent tracking, data-deletion requests

---

## Troubleshooting

**Backend won't start**
```bash
cd backend && ..\.venv\Scripts\python -m uvicorn app.main:app --reload
```

**App can't connect to backend**
- Android emulator auto-uses `10.0.2.2:8000`
- Physical device: use your machine's LAN IP via `--dart-define=API_BASE_URL=http://192.168.1.100:8000`

**Flutter build errors**
```bash
cd health_app && flutter clean && flutter pub get && flutter run
```

**Database errors**
```bash
cd backend && ..\.venv\Scripts\python -m alembic upgrade head
```

---

## Commands Reference

```bash
# Backend
cd backend && ..\.venv\Scripts\python -m uvicorn app.main:app --reload
cd backend && ..\.venv\Scripts\python -m pytest -v
cd backend && ..\.venv\Scripts\python -m alembic upgrade head

# Frontend
cd health_app && flutter run
cd health_app && flutter clean
cd health_app && flutter pub get
cd health_app && flutter build apk --release
```

---

## Useful Links

- Full setup guide: `SETUP_AND_RUN.md`
- System overview: `SYSTEM_STATUS.md`
- Master reference: `MASTER_REFERENCE.md`
- UI documentation: `health_app/README_UI.md`
- Backend readme: `backend/README.md`
