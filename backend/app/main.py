import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST

from app.config import get_settings
from app.database import Base, engine
from app.services.scheduler import start_scheduler, stop_scheduler
from app.models import user
import app.models.chat
import app.models.health
import app.models.diet
import app.models.sleep
import app.models.privacy
import app.models.token_revocation
import app.models.background_task
import app.models.doctor
import app.models.consultation
import app.models.prescription
import app.models.audit_log
from app.routes import user as user_routes
from app.routes import health as health_routes
from app.routes import diet as diet_routes
from app.routes import sleep as sleep_routes
from app.routes import insights as insights_routes
from app.routes import chat
from app.routes import privacy as privacy_routes
from app.routes import scan as scan_routes
from app.routes import doctors as doctors_routes
from app.routes import consultations as consultations_routes
from app.routes import prescriptions as prescriptions_routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
settings = get_settings()

try:
    import sentry_sdk

    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
except Exception:
    pass

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request duration in seconds", ["method", "path"]
)

# Create tables only in non-production environments.
if settings.is_development or settings.ENVIRONMENT.lower() == "test":
    Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENABLE_SCHEDULER:
        start_scheduler()
    try:
        yield
    finally:
        if settings.ENABLE_SCHEDULER:
            stop_scheduler()


app = FastAPI(
    title=settings.API_TITLE,
    description="Heallio API with chatbot support",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS with environment-specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    duration_sec = duration_ms / 1000
    response.headers["x-request-id"] = request_id
    # Label by the matched route template (e.g. "/consultations/{ticket_id}") not
    # the raw URL, so path params don't explode Prometheus label cardinality.
    route = request.scope.get("route")
    path_label = getattr(route, "path", None) or "__unmatched__"
    REQUEST_COUNT.labels(request.method, path_label, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(request.method, path_label).observe(duration_sec)
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors with detailed response."""
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": str(exc.errors())},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/", tags=["Health"])
def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "service": "Heallio API",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/live", tags=["Health"])
def liveness_probe():
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
def readiness_probe():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as e:
        logger.error("Readiness probe failed: %s", str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "error"},
        )


@app.get("/metrics", tags=["Health"])
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Include all routers
app.include_router(user_routes.router, tags=["Users"])
app.include_router(health_routes.router, tags=["Health"])
app.include_router(diet_routes.router, tags=["Diet"])
app.include_router(sleep_routes.router, tags=["Sleep"])
app.include_router(insights_routes.router, tags=["Insights"])
app.include_router(chat.router, tags=["Chat"])
app.include_router(privacy_routes.router, tags=["Privacy"])
app.include_router(scan_routes.router, tags=["Scan"])
app.include_router(doctors_routes.router, tags=["Doctors"])
app.include_router(consultations_routes.router, tags=["Consultations"])
app.include_router(prescriptions_routes.router, tags=["Prescriptions"])

logger.info(f"Application started in {settings.ENVIRONMENT} mode")
logger.info(f"CORS enabled for origins: {settings.ALLOWED_ORIGINS}")




