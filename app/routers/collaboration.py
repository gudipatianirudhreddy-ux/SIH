import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import require_authenticated_user, require_role
from app.database import get_db
from app.models.profile import Profile
from app.schemas.collaboration import CollaborationResponse
from app.services import collaboration as collaboration_service

router = APIRouter(tags=["collaborations"])


@router.post(
    "/applications/{application_id}/select",
    response_model=CollaborationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Select a student proposal and start collaboration",
    description="Allows an Industrialist to select a pending student application and start an active collaboration for the issue.",
)
def select_application(
    application_id: uuid.UUID,
    industrialist: Profile = Depends(require_role("INDUSTRY")),
    db: Session = Depends(get_db),
):
    return collaboration_service.select_application_and_create_collaboration(
        db=db,
        application_id=application_id,
        industrialist=industrialist,
    )


@router.get("/collaborations/me", response_model=List[CollaborationResponse])
def get_my_collaborations(
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    return collaboration_service.list_my_collaborations(db, current_profile)


@router.get("/collaborations/{collaboration_id}", response_model=CollaborationResponse)
def get_collaboration(
    collaboration_id: uuid.UUID,
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    return collaboration_service.get_collaboration(db, collaboration_id, current_profile)
