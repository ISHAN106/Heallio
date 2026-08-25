from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.token_revocation import RefreshTokenRevocation


def revoke_refresh_token(
    db: Session, jti: str, user_email: str | None, exp_timestamp: int | float
) -> None:
    existing = (
        db.query(RefreshTokenRevocation)
        .filter(RefreshTokenRevocation.jti == jti)
        .first()
    )
    if existing:
        return

    expires_at = datetime.fromtimestamp(float(exp_timestamp), tz=timezone.utc).replace(
        tzinfo=None
    )
    db.add(
        RefreshTokenRevocation(
            jti=jti,
            user_email=user_email,
            revoked_at=datetime.utcnow(),
            expires_at=expires_at,
        )
    )
    db.commit()


def is_refresh_token_revoked(db: Session, jti: str) -> bool:
    now = datetime.utcnow()

    # Opportunistic cleanup of expired revocations.
    db.query(RefreshTokenRevocation).filter(RefreshTokenRevocation.expires_at <= now).delete()
    db.commit()

    exists = (
        db.query(RefreshTokenRevocation)
        .filter(RefreshTokenRevocation.jti == jti)
        .first()
    )
    return exists is not None
