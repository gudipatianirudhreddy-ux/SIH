from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class CollaborationResponse(BaseModel):
    id: uuid.UUID
    issue_id: uuid.UUID
    application_id: uuid.UUID
    student_id: uuid.UUID
    industrialist_id: uuid.UUID
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
