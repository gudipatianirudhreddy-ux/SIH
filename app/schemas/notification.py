from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    message: str
    related_issue_id: Optional[uuid.UUID] = None
    related_application_id: Optional[uuid.UUID] = None
    related_collaboration_id: Optional[uuid.UUID] = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    page: int
    page_size: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    count: int
