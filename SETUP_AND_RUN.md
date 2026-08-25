# Setup & Running Guide

## ✅ Prerequisites Installed
- ✅ Flutter dependencies installed (riverpod, http, shared_preferences)
- ✅ Backend FastAPI server running on `http://localhost:8000`
- ✅ API client configured with platform-specific URLs
- ✅ CORS enabled for localhost

## 🚀 Quick Start

### 1. Backend is Already Running ✅
The FastAPI backend is currently running with:
- Port: 8000
- Host: 0.0.0.0
- Status: ✅ Alive and responding
- Database: SQLite (development) / PostgreSQL (production)
- Scheduler: APScheduler jobs registered

### 2. Flutter App Setup

#### Update pubspec.yaml (already done)
```yaml
dependencies:
  flutter_riverpod: ^2.4.9
  http: ^1.2.2
  shared_preferences: ^2.3.2
```

#### Install Flutter Dependencies (already done)
```bash
cd health_app
flutter pub get
```

### 3. Run the Flutter App

#### Android/iOS Device or Emulator
```bash
cd health_app
flutter run
```

#### Web (if you have web enabled)
```bash
cd health_app
flutter run -d web
```

#### Desktop (Windows/Mac/Linux)
```bash
cd health_app
flutter run -d windows    # or macos/linux
```

## 🔌 Backend Configuration

### Platform-Specific URLs (Auto-handled)
The app automatically uses the correct URL based on platform:
- **localhost/web:** `http://localhost:8000`
- **Android emulator:** `http://10.0.2.2:8000`
- **iOS simulator:** `http://127.0.0.1:8000`
- **Physical device:** `http://your-machine-ip:8000`

### Configuration File
Location: `health_app/lib/config/app_config.dart`
- Dev API URL: `http://localhost:8000`
- Environment: `development`
- Feature flags and timeouts configurable

## 🔐 Default Test Credentials

After running the backend migrations:
- You can create new accounts via the Signup screen
- Or test with API using curl:

```bash
# Create account
curl -X POST http://localhost:8000/users/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"password123"}'

# Login
curl -X POST http://localhost:8000/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

## 🧪 Testing the Connection

### Test Backend Health
```bash
curl http://localhost:8000/health/live
# Response: {"status":"alive"}
```

### Test Backend Readiness
```bash
curl http://localhost:8000/health/ready
# Response: {"status":"ready"}
```

### View Prometheus Metrics
```
http://localhost:8000/metrics
```

## 📱 Running the Complete Stack

### Terminal 1: Backend (ALREADY RUNNING)
```bash
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: Flutter App
```bash
cd health_app
flutter run
```

## 🐛 Troubleshooting

### App Cannot Connect to Backend

**Issue:** Connection refused or timeout
**Solutions:**
1. Check backend is running: `curl http://localhost:8000/health/live`
2. Verify port 8000 is not blocked
3. For Android emulator, ensure using `10.0.2.2:8000` (auto-handled)
4. For physical device, use machine IP instead of localhost

### Flutter Pub Get Fails
```bash
flutter clean
flutter pub get
```

### Backend Connection Errors
```bash
# Check if backend is running
curl http://localhost:8000/health/live

# If not, restart it:
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload
```

### Models/API mismatch
- Ensure backend migrations are up to date: `alembic upgrade head`
- Both frontend models and backend schemas should match

## 📊 Available Endpoints

### Authentication
- `POST /users/signup` - Create account
- `POST /users/login` - Login
- `POST /users/refresh` - Refresh token
- `POST /users/logout` - Logout
- `GET /users/me` - Current user

### Health Data
- `GET /health` - Get health records
- `POST /health/record` - Log health data
- `GET /diet` - Get diet records
- `POST /diet/record` - Log meal
- `GET /sleep` - Get sleep records
- `POST /sleep/record` - Log sleep

### AI Features
- `POST /chat` - Send message
- `GET /chat/history` - Chat history
- `GET /insights` - Get insights

### Privacy
- `POST /privacy/consent` - Grant consent
- `GET /privacy/consent/me` - Get consent status
- `POST /privacy/delete-request` - Request data deletion

### Monitoring
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe
- `GET /metrics` - Prometheus metrics

## 🔄 Workflow

1. **Start Backend** ✅ (Already running)
2. **Open Flutter App with:**
   ```bash
   cd health_app && flutter run
   ```
3. **App automatically connects to backend** (platform-aware URLs)
4. **Create account** via signup or test login
5. **Grant consent** to use AI chat
6. **Log health data** and get insights

## 🚀 Next Steps

1. Choose a device/emulator:
   - Android emulator (recommended for development)
   - iOS simulator
   - Physical device
   - Web browser

2. Run Flutter app:
   ```bash
   cd health_app
   flutter run
   ```

3. Test the features:
   - Create account
   - Log health data
   - Chat with AI
   - View insights

## 📝 Environment Variables (Optional)

Can override API URL via environment:
```bash
flutter run -d android --dart-define=API_BASE_URL=http://192.168.1.100:8000
```

## ✅ Verification Checklist

- [x] Backend running on port 8000
- [x] Flutter dependencies installed
- [x] API client configured
- [x] CORS enabled
- [x] Database migrations applied
- [ ] Flutter app started with `flutter run`
- [ ] Able to signup/login
- [ ] Can view home dashboard
- [ ] Chat works after consent
- [ ] Health data logging works

## 📞 Support

If you encounter issues:
1. Check backend logs: Terminal where backend is running
2. Check Flutter logs: Output of `flutter run`
3. Verify connectivity: `curl http://localhost:8000/health/live`
4. Check database: `sqlite:///./test.db` (default dev DB)
