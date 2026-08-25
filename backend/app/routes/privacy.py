from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.privacy import DataDeletionRequest, UserConsent
from app.models.user import User
from app.schemas.privacy import (
    ConsentResponse,
    ConsentUpdateRequest,
    DataDeletionRequestCreate,
    DataDeletionRequestResponse,
)
from app.services.auth import get_current_user_email


router = APIRouter(prefix="/privacy", tags=["Privacy"])


@router.post("/consent", response_model=ConsentResponse)
def update_consent(
    payload: ConsentUpdateRequest,
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email),
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    consent = db.query(UserConsent).filter(UserConsent.user_id == user.id).first()
    if not consent:
        consent = UserConsent(user_id=user.id)
        db.add(consent)

    consent.consent_given = payload.consent_given
    consent.consent_version = payload.consent_version
    consent.updated_at = datetime.utcnow()
    if payload.consent_given:
        consent.granted_at = datetime.utcnow()
    else:
        consent.revoked_at = datetime.utcnow()

    db.commit()
    db.refresh(consent)

    return ConsentResponse(
        consent_given=consent.consent_given,
        consent_version=consent.consent_version,
        granted_at=consent.granted_at,
        revoked_at=consent.revoked_at,
        updated_at=consent.updated_at,
    )


@router.get("/consent/me", response_model=ConsentResponse)
def get_consent(
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email),
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    consent = db.query(UserConsent).filter(UserConsent.user_id == user.id).first()
    if not consent:
        return ConsentResponse(
            consent_given=False,
            consent_version="v1",
            granted_at=None,
            revoked_at=None,
            updated_at=datetime.utcnow(),
        )

    return ConsentResponse(
        consent_given=consent.consent_given,
        consent_version=consent.consent_version,
        granted_at=consent.granted_at,
        revoked_at=consent.revoked_at,
        updated_at=consent.updated_at,
    )


@router.post("/delete-request", response_model=DataDeletionRequestResponse)
def request_data_deletion(
    payload: DataDeletionRequestCreate,
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email),
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    deletion_request = DataDeletionRequest(
        user_id=user.id,
        reason=payload.reason,
        status="pending",
        requested_at=datetime.utcnow(),
    )
    db.add(deletion_request)
    db.commit()
    db.refresh(deletion_request)
    return deletion_request
