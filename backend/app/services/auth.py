from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.session import UserSession
from app.models.user import User
from app.services.jwt import decode_token

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


def token_issued_before_revocation(payload: dict, user: User) -> bool:
    """True if this token predates the user's last global revocation (logout).

    JWT `iat` has 1-second resolution, so we compare with `<=`: a token issued in
    the same second as the logout is treated as revoked. This keeps logout
    reliable (revokes everything issued up to that second); the only cost is that
    a full re-login within the same second would also be rejected, which isn't
    reachable through the UI. A missing `iat` fails closed (treated as revoked).
    """
    revoked_at = getattr(user, "tokens_valid_from", None)
    if revoked_at is None:
        return False
    iat = payload.get("iat")
    if iat is None:
        return True
    return datetime.utcfromtimestamp(iat) <= revoked_at


def is_session_revoked(db: Session, sid: str | None) -> bool:
    """True if `sid` names an individually-revoked session (e.g. via
    DELETE /users/me/sessions/{id}). `sid` is absent on tokens issued before
    session tracking existed — treat those as untracked rather than revoked.
    """
    if sid is None:
        return False
    session = db.query(UserSession).filter(UserSession.session_id == sid).first()
    return session is not None and session.revoked_at is not None


def get_current_user_email(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> str:
    """
    Extract and validate the current user's email from a JWT access token.

    Rejects refresh tokens and tokens revoked by a prior logout.

    Raises:
        HTTPException: If token is invalid, expired, or revoked.
    """
    try:
        payload = decode_token(token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from e

    if payload.get("token_type") == "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cannot be used to authenticate requests",
        )

    email: str | None = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account has been deactivated.",
        )

    if token_issued_before_revocation(payload, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked. Please log in again.",
        )

    if is_session_revoked(db, payload.get("sid")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This session has been signed out.",
        )

    return email


def get_current_session_id(token: str = Depends(oauth2_scheme)) -> str | None:
    """Best-effort session id from the current access token, for endpoints
    that need to mark "this is the session you're calling from" (e.g. the
    connected-sessions list). Returns None for tokens issued before session
    tracking existed or on any decode failure — callers should treat that as
    "no session matches", not an error.
    """
    try:
        payload = decode_token(token)
    except JWTError:
        return None
    return payload.get("sid")


def get_current_user(
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.email == current_user_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def require_role(*roles: str):
    def role_dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_dependency