from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SponsorshipStatus
from app.schemas.profile import ProfileResponse


class SponsorshipBase(BaseModel):
    amount: float = Field(..., ge=0.0, description="Pledged sponsorship amount (non-negative)")
    message: Optional[str] = Field(default=None, description="Sponsorship, grant, or mentorship note")


class SponsorshipCreate(SponsorshipBase):
    pass


class SponsorshipUpdate(BaseModel):
    amount: Optional[float] = Field(default=None, ge=0.0, description="Updated amount")
    message: Optional[str] = Field(default=None, description="Updated message")
    status: Optional[SponsorshipStatus] = Field(default=None, description="Updated status")


class SponsorshipResponse(SponsorshipBase):
    id: uuid.UUID
    issue_id: uuid.UUID
    industrialist_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
    industrialist: Optional[ProfileResponse] = None

    model_config = ConfigDict(from_attributes=True)
