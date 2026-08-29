from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models import NotificationType


class NotificationCreateSchema(BaseModel):
    title: str
    body: Optional[str] = None
    notification_type: Optional[NotificationType] = NotificationType.SYSTEM


class NotificationUpdateSchema(BaseModel):
    is_read: bool


class NotificationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    title: str
    body: Optional[str] = None
    notification_type: Optional[NotificationType] = None
    is_read: bool = False
    created_at: Optional[datetime] = None