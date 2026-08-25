from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: int
    device_label: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    last_seen_at: Optional[datetime] = None
    is_current: bool

    model_config = {"from_attributes": True}
