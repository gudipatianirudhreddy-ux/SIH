import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.schemas.profile import ProfileCreate, ProfileResponse, ProfileUpdate
from app.services import profile as profile_service

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _extract_user_uuid(user: Any) -> uuid.UUID:
    try:
        user_id = getattr(user, "id", None)
        if user_id is None:
            raise ValueError("User object has no id attribute")
        return uuid.UUID(str(user_id))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in authentication token",
        ) from exc


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = _extract_user_uuid(current_user)
    db_profile = profile_service.get_profile_by_user_id(db, user_id)
    if not db_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    return db_profile


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
@router.post("/me", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_my_profile(
    profile_in: ProfileCreate,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = _extract_user_uuid(current_user)
    return profile_service.create_profile(db, user_id, profile_in)


@router.patch("/me", response_model=ProfileResponse)
@router.put("/me", response_model=ProfileResponse)
def update_my_profile(
    profile_in: ProfileUpdate,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = _extract_user_uuid(current_user)
    return profile_service.update_profile(db, user_id, profile_in)
