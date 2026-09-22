from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict
from app.models.enums import CollaborationStatus


class CollaborationUpdate(BaseModel):
    status: CollaborationStatus


class CollaborationResponse(BaseModel):
    id: uuid.UUID
    issue_id: uuid.UUID
    application_id: uuid.UUID
    student_id: uuid.UUID
    industrialist_id: uuid.UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

