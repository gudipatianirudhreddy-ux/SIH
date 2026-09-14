import os
from typing import Any, Callable
import uuid

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from supabase import Client, create_client

from app.database import get_db
from app.models.profile import Profile

load_dotenv()
security = HTTPBearer(auto_error=True)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")

supabase: Client = create_client(
    SUPABASE_URL or "",
    SUPABASE_PUBLISHABLE_KEY or "",
)


def get_current_user(credentials=Depends(security)):
    cred = credentials.credentials
    response = supabase.auth.get_user(cred)
    if not response.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return response.user


def extract_user_uuid(user: Any) -> uuid.UUID:
    """Extract uuid.UUID from user object or dictionary."""
    try:
        user_id = getattr(user, "id", None)
        if user_id is None and isinstance(user, dict):
            user_id = user.get("id")
        if user_id is None:
            raise ValueError("User object has no id attribute")
        return uuid.UUID(str(user_id))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in authentication token",
        ) from exc


def require_authenticated_user(
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    """Ensure user is authenticated and has a valid Profile in database."""
    user_id = extract_user_uuid(current_user)
    profile = db.query(Profile).filter(Profile.id == user_id).first()
    if not profile:
        # Default citizen profile if user signed in but hasn't filled out details yet
        user_email = getattr(current_user, "email", None)
        display_name = user_email.split("@")[0] if user_email else "Citizen"
        profile = Profile(
            id=user_id,
            name=display_name,
            role="citizen",
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def require_role(*allowed_roles: str) -> Callable[..., Profile]:
    """Dependency factory checking that the authenticated user possesses one of the allowed roles."""
    normalized_allowed = set()
    for r in allowed_roles:
        r_clean = r.strip().lower()
        normalized_allowed.add(r_clean)
        if r_clean in ("industry", "industrialist"):
            normalized_allowed.add("industry")
            normalized_allowed.add("industrialist")

    def role_dependency(
        profile: Profile = Depends(require_authenticated_user),
    ) -> Profile:
        user_role = (profile.role or "").strip().lower()
        if user_role == "admin" or user_role in normalized_allowed:
            return profile
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation not permitted. Required role: {', '.join(allowed_roles)} (current role: {profile.role})",
        )

    return role_dependency


require_student = require_role("STUDENT")
require_industry = require_role("INDUSTRY")
require_admin = require_role("ADMIN")
