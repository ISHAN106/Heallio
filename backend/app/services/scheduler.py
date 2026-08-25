import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.models.token_revocation import RefreshTokenRevocation

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="UTC")


def cleanup_expired_revocations() -> None:
    db = SessionLocal()
    try:
        deleted = (
            db.query(RefreshTokenRevocation)
            .filter(RefreshTokenRevocation.expires_at <= datetime.utcnow())
            .delete()
        )
        db.commit()
        if deleted:
            logger.info("Scheduler cleanup removed %s expired token revocations", deleted)
    except Exception as e:
        db.rollback()
        logger.error("Scheduler cleanup failed: %s", str(e))
    finally:
        db.close()


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        cleanup_expired_revocations,
        trigger="interval",
        minutes=30,
        id="cleanup_expired_revocations",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Background scheduler started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
