import logging
import re
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models.doctor import DoctorCategory, DoctorProfile
from app.models.session import UserSession
from app.models.user import User
from app.schemas.user import RefreshTokenRequest, UserCreate, UserResponse
from app.services.account_lockout import account_lockout_service
from app.services.audit import write_audit_log
from app.services.rate_limit import rate_limiter
from app.services.security import hash_password, verify_password, validate_password
from app.services.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    is_refresh_token,
)
from app.schemas.session import SessionResponse
from app.services.token_blocklist import is_refresh_token_revoked, revoke_refresh_token
from app.services.auth import (
    get_current_session_id,
    get_current_user_email,
    is_session_revoked,
    token_issued_before_revocation,
)

logger = logging.getLogger(__name__)
settings = get_settings()

DEFAULT_DOCTOR_CATEGORY_NAME = "General"

# Router definition
router = APIRouter(prefix="/users", tags=["Users"])


def normalize_email(email: str) -> str:
    return email.strip().lower()


# DB dependency
def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------
# SIGNUP
# --------------------
@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, request: Request, db: Session = Depends(get_db)):
    """
    Register a new user.

    - **name**: User's full name
    - **email**: User's email (must be unique)
    - **password**: Password (min 8 chars, uppercase, lowercase, digit, special char)
    """
    client_ip = request.client.host if request.client else "unknown"
    # Same limit/window as login — signup's "email already registered" response
    # is otherwise an unthrottled account-enumeration oracle.
    if not rate_limiter.allow(
        f"signup:{client_ip}",
        limit=settings.LOGIN_RATE_LIMIT,
        window_seconds=settings.LOGIN_RATE_WINDOW_SECONDS,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many signup attempts. Please try again later.",
        )

    try:
        normalized_email = normalize_email(user.email)

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", user.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format",
            )

        # Validate password strength
        validate_password(user.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Check if email already exists
    db_user = (
        db.query(User)
        .filter(User.email.ilike(normalized_email))
        .first()
    )
    if db_user:
        logger.warning(f"Signup attempted with existing email: {normalized_email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    try:
        default_category = None
        if user.role == "doctor":
            default_category = (
                db.query(DoctorCategory)
                .filter(DoctorCategory.name == DEFAULT_DOCTOR_CATEGORY_NAME)
                .first()
            )
            if not default_category:
                default_category = DoctorCategory(
                    name=DEFAULT_DOCTOR_CATEGORY_NAME,
                    description="Auto-created default category",
                )
                db.add(default_category)
                db.flush()

        new_user = User(
            name=user.name,
            email=normalized_email,
            password=hash_password(user.password),
            role=user.role,
        )
        db.add(new_user)
        db.flush()

        if user.role == "doctor" and default_category is not None:
            db.add(
                DoctorProfile(
                    user_id=new_user.id,
                    category_id=default_category.id,
                    license_number=f"AUTO-{new_user.id}",
                    years_experience=0,
                    bio="Auto-generated doctor profile",
                    is_available=True,
                )
            )

        db.commit()
        db.refresh(new_user)
        write_audit_log(
            db,
            actor_user_id=new_user.id,
            actor_role=new_user.role,
            event_type="user_signed_up",
            target_type="user",
            target_id=str(new_user.id),
            severity="info",
            metadata={"email": new_user.email},
        )
        logger.info(f"New user registered: {normalized_email}")
        return new_user
    except Exception as e:
        db.rollback()
        logger.error(f"Error during user registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user",
        ) from e


# --------------------
# LOGIN (OAuth2)
# --------------------
@router.post("/login")
async def login_user(request: Request, db: Session = Depends(get_db)):
    """
    Login and get access token.
    
    - **username**: User's email
    - **password**: User's password
    
    Returns JWT access token for authenticated requests.
    """
    client_ip = request.client.host if request.client else "unknown"
    key = f"login:{client_ip}"
    if not rate_limiter.allow(
        key,
        limit=settings.LOGIN_RATE_LIMIT,
        window_seconds=settings.LOGIN_RATE_WINDOW_SECONDS,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    content_type = request.headers.get("content-type", "")
    username = None
    password = None
    requested_role = "user"

    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            body = {}
        username = body.get("username") or body.get("email")
        password = body.get("password")
        requested_role = str(body.get("role") or "user")
    else:
        form = await request.form()
        username = form.get("username") or form.get("email")
        password = form.get("password")
        requested_role = str(form.get("role") or "user")

    if username:
        username = normalize_email(str(username))
    requested_role = requested_role.strip().lower()
    if requested_role not in {"user", "doctor"}:
        requested_role = "user"

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="username/email and password are required",
        )

    # Keyed by account only (not account+IP) — an attacker rotating source IPs
    # must not get a fresh attempt counter per IP. Per-IP throttling is handled
    # separately by the rate_limiter check above.
    lock_identifier = username
    if account_lockout_service.is_locked(lock_identifier):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to repeated failed logins.",
        )

    db_user = db.query(User).filter(User.email.ilike(username)).first()

    # Verify identity (existence + password) fully before checking role, and
    # use the same generic message for both failure modes. Checking role first
    # would let a caller distinguish "no such account" from "wrong portal for
    # this account" without ever supplying a valid password — an enumeration
    # oracle. Only after a valid password is presented do we reveal anything
    # role-specific, which is safe because the caller has now proven they
    # legitimately control the account.
    if not db_user or not verify_password(password, db_user.password):
        # No silent account creation on login. Unknown accounts fail like a bad
        # password (generic message avoids account enumeration); users must sign
        # up through /users/signup, which enforces the password policy.
        account_lockout_service.register_failure(
            lock_identifier,
            max_attempts=settings.MAX_FAILED_LOGIN_ATTEMPTS,
            lockout_seconds=settings.LOGIN_LOCKOUT_SECONDS,
        )
        logger.warning(f"Login failed: invalid credentials for {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if requested_role == "doctor" and db_user.role != "doctor":
        logger.warning(f"Doctor login failed: role mismatch for {username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not a doctor account. Please use the doctor portal.",
        )

    if requested_role == "user" and db_user.role == "doctor":
        logger.warning(f"User login blocked for doctor account: {username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is a doctor account. Please use the doctor portal.",
        )

    if not db_user.is_active:
        logger.warning(f"Login blocked for deactivated account: {username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    account_lockout_service.reset(lock_identifier)

    session_id = str(uuid4())
    db.add(
        UserSession(
            user_id=db_user.id,
            session_id=session_id,
            # Raw User-Agent string, capped defensively — no UA-parsing
            # dependency needed just to show a device label.
            device_label=(request.headers.get("user-agent") or "Unknown device")[:255],
            ip_address=client_ip,
            created_at=datetime.utcnow(),
        )
    )
    db.commit()

    token = create_access_token({"sub": db_user.email, "sid": session_id})
    refresh_token = create_refresh_token({"sub": db_user.email, "sid": session_id})
    write_audit_log(
        db,
        actor_user_id=db_user.id,
        actor_role=db_user.role,
        event_type="user_logged_in",
        target_type="user",
        target_id=str(db_user.id),
        severity="info",
        metadata={"email": db_user.email},
    )
    logger.info(f"User logged in: {username}")

    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "name": db_user.name,
            "username": db_user.name,
            "role": db_user.role,
        },
    }


@router.post("/refresh")
def refresh_access_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Issue a new access token from a valid refresh token."""
    try:
        decoded = decode_token(payload.refresh_token)
        if not is_refresh_token(decoded):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        email = decoded.get("sub")
        jti = decoded.get("jti")
        if not jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        if is_refresh_token_revoked(db, jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Reject refresh tokens invalidated by a global logout.
        user = db.query(User).filter(User.email == email).first()
        if not user or token_issued_before_revocation(decoded, user):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )

        # Reject refresh tokens whose specific session was signed out via
        # DELETE /users/me/sessions/{id} (global logout is checked above).
        sid = decoded.get("sid")
        if is_session_revoked(db, sid):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="This session has been signed out.",
            )

        access_claims = {"sub": email}
        if sid:
            access_claims["sid"] = sid
        new_access_token = create_access_token(access_claims)
        return {"access_token": new_access_token, "token_type": "bearer"}
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from e


@router.post("/logout")
def logout(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Revoke a refresh token JTI to invalidate future refresh requests."""
    try:
        decoded = decode_token(payload.refresh_token)
        if not is_refresh_token(decoded):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        jti = decoded.get("jti")
        exp = decoded.get("exp")
        if not jti or not exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        revoke_refresh_token(db, jti, decoded.get("sub"), exp)

        # Revoke every outstanding access + refresh token for this user so the
        # short-lived access token can't outlive logout.
        email = decoded.get("sub")
        if email:
            user = db.query(User).filter(User.email == email).first()
            if user:
                user.tokens_valid_from = datetime.utcnow()
                db.commit()

        sid = decoded.get("sid")
        if sid:
            session = db.query(UserSession).filter(UserSession.session_id == sid).first()
            if session:
                session.revoked_at = datetime.utcnow()
                db.commit()
        return {"message": "Logged out successfully"}
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from e


# --------------------
# GET CURRENT USER
# --------------------
@router.get("/me", response_model=dict)
def read_me(
    current_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Get current authenticated user's profile details.
    
    Requires valid JWT token in Authorization header.
    """
    user = db.query(User).filter(User.email == current_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "username": user.name,
        "role": user.role,
    }


# --------------------
# CONNECTED SESSIONS
# --------------------
@router.get("/me/sessions", response_model=list[SessionResponse])
def list_my_sessions(
    current_email: str = Depends(get_current_user_email),
    current_sid: str | None = Depends(get_current_session_id),
    db: Session = Depends(get_db),
):
    """List the caller's active (non-revoked) login sessions/devices."""
    user = db.query(User).filter(User.email == current_email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .order_by(UserSession.created_at.desc())
        .all()
    )
    return [
        SessionResponse(
            id=s.id,
            device_label=s.device_label,
            ip_address=s.ip_address,
            created_at=s.created_at,
            last_seen_at=s.last_seen_at,
            is_current=(s.session_id == current_sid),
        )
        for s in sessions
    ]


@router.delete("/me/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_my_session(
    session_id: int,
    current_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Sign out one of the caller's own devices/sessions."""
    user = db.query(User).filter(User.email == current_email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    session = (
        db.query(UserSession)
        .filter(UserSession.id == session_id, UserSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session.revoked_at = datetime.utcnow()
    db.commit()