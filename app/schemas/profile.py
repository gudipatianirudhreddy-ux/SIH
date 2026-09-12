from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class UserRole(str, Enum):
    CITIZEN = "citizen"
    STUDENT = "student"
    INDUSTRY = "industry"


class ProfileBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: UserRole


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    role: Optional[UserRole] = None


class ProfileResponse(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
