from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class RefreshTokenRevocation(Base):
    __tablename__ = "refresh_token_revocations"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, unique=True, nullable=False, index=True)
    user_email = Column(String, nullable=True, index=True)
    revoked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
