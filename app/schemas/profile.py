from datetime import datetime
from enum import Enum
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

class UserRole(str, Enum):
    CITIZEN = "citizen"
    STUDENT = "student"
    INDUSTRIALIST = "industrialist"
class ProfileBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: UserRole
    phone_number: Optional[str] = Field(default=None, pattern=r"^\+?[0-9\s\-()]{7,25}$")
    avatar_url: Optional[str] = None
    location: Optional[str] = Field(default=None, max_length=255)
class ProfileCreate(ProfileBase): pass
class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    role: Optional[UserRole] = None
    phone_number: Optional[str] = Field(default=None, pattern=r"^\+?[0-9\s\-()]{7,25}$")
    avatar_url: Optional[str] = None
    location: Optional[str] = Field(default=None, max_length=255)
class ProfileResponse(BaseModel):
    id: uuid.UUID
    name: str
    phone_number: Optional[str] = None
    role: str
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    points: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
