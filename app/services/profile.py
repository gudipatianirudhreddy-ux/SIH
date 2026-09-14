import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.schemas.profile import ProfileCreate, ProfileUpdate, UserRole


def get_profile_by_user_id(db: Session, user_id: uuid.UUID) -> Optional[Profile]:
    return db.query(Profile).filter(Profile.id == user_id).first()


def create_profile(db: Session, user_id: uuid.UUID, profile_data: ProfileCreate) -> Profile:
    existing = get_profile_by_user_id(db, user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already exists for this user",
        )

    role_val = profile_data.role.value if isinstance(profile_data.role, UserRole) else str(profile_data.role)
    db_profile = Profile(
        id=user_id,
        name=profile_data.name,
        role=role_val,
        phone_number=profile_data.phone_number,
        avatar_url=profile_data.avatar_url,
        location=profile_data.location,
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


def update_profile(db: Session, user_id: uuid.UUID, profile_data: ProfileUpdate) -> Profile:
    db_profile = get_profile_by_user_id(db, user_id)
    if not db_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    if profile_data.name is not None:
        db_profile.name = profile_data.name
    if profile_data.role is not None:
        db_profile.role = profile_data.role.value if isinstance(profile_data.role, UserRole) else str(profile_data.role)
    if profile_data.phone_number is not None:
        db_profile.phone_number = profile_data.phone_number
    if profile_data.avatar_url is not None:
        db_profile.avatar_url = profile_data.avatar_url
    if profile_data.location is not None:
        db_profile.location = profile_data.location

    db.commit()
    db.refresh(db_profile)
    return db_profile
