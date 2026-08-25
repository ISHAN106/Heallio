Heallio Backend

Run backend:

1. Activate your virtual environment.
2. Install dependencies from requirements.txt.
3. Start API:
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

Database migrations (Alembic):

1. Apply migrations:
	alembic upgrade head
2. Create a new migration:
	alembic revision -m "describe_change"
3. If your database existed before Alembic was added, mark current schema as applied first:
	alembic stamp head

Backend tests:

1. Run API tests:
	pytest -q

Connect the backend to PostgreSQL:

1. Make sure PostgreSQL is running.
2. Set `DATABASE_URL` in `.env`:

	Local development:
	DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/ai_health

	Docker Compose:
	DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/ai_health

3. Install dependencies if needed:

	pip install -r requirements.txt

4. Apply the schema to PostgreSQL:

	alembic upgrade head

5. Start the API:

	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

Privacy/compliance endpoints:

- POST /privacy/consent
- GET /privacy/consent/me
- POST /privacy/delete-request

Chat access requires active privacy consent.

Background scheduler:

- Weekly insights are computed on demand by GET /insights/weekly (no background queue).
- APScheduler runs every 30 minutes to purge expired refresh-token revocations.

Deployment note (single worker):

- Login rate limiting and account lockout are in-process (per worker). Run the API
  with a single worker (the default), or move that state to a shared store (Redis)
  before scaling to multiple workers, otherwise limits are enforced per-worker.

Chatbot:

- The `/chat/` endpoint is backed by the Groq Chat Completions API (`ml/chatbot/llm_engine.py`), not a locally trained intent model. Groq has a free tier and exposes an OpenAI-compatible API, so the `openai` SDK is reused with a custom `base_url`.
- Configure via env vars: GROQ_API_KEY, GROQ_MODEL (default llama-3.3-70b-versatile), CHAT_MAX_TOKENS (default 512). Get a free key at https://console.groq.com/keys.
- `ml/chatbot/safety.py` still runs a deterministic crisis/dangerous-medical-message check before every LLM call.

Mobile app API base URL:

- Flutter now supports API endpoint override via dart define:
	flutter run --dart-define=API_BASE_URL=http://<your-host>:8000
- Defaults:
	- Android emulator: http://10.0.2.2:8000
	- Web: http://localhost:8000
	- Desktop/iOS simulator: http://127.0.0.1:8000

	Production (Docker + Postgres):

	1. Build and run services:
		docker compose up --build
	2. Backend runs on http://localhost:8000 with Postgres and Alembic migration on startup.
	3. Monitoring:
		- Prometheus: http://localhost:9090
		- Grafana: http://localhost:3001 (admin/admin)

	CI pipeline:

	- GitHub Actions workflow runs Alembic migration + pytest on backend changes.
