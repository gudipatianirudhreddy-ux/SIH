from typing import List
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import require_authenticated_user, require_role
from app.database import get_db
from app.models.profile import Profile
from app.schemas.sponsorship import (
    SponsorshipCreate,
    SponsorshipResponse,
    SponsorshipUpdate,
)
from app.services import sponsorship as sponsorship_service

router = APIRouter(tags=["sponsorships"])


@router.post(
    "/issues/{issue_id}/sponsorships",
    response_model=SponsorshipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Pledge sponsorship for an issue",
    description="Allows industry representatives to pledge financial support, materials, or grant assistance for an issue.",
)
def create_sponsorship(
    issue_id: uuid.UUID,
    sponsorship_in: SponsorshipCreate,
    industry_profile: Profile = Depends(require_role("INDUSTRY")),
    db: Session = Depends(get_db),
):
    return sponsorship_service.create_sponsorship(
        db=db,
        issue_id=issue_id,
        industrialist_profile=industry_profile,
        sponsorship_in=sponsorship_in,
    )


@router.get(
    "/issues/{issue_id}/sponsorships",
    response_model=List[SponsorshipResponse],
    summary="List sponsorships for an issue",
    description="Retrieves pledged sponsorships for an issue. Accessible by reporter, industry partners, and administrators.",
)
def list_issue_sponsorships(
    issue_id: uuid.UUID,
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    return sponsorship_service.list_sponsorships_for_issue(
        db=db,
        issue_id=issue_id,
        current_profile=current_profile,
    )


@router.patch(
    "/sponsorships/{sponsorship_id}",
    response_model=SponsorshipResponse,
    summary="Update sponsorship",
    description="Allows industrialists to modify their pledged amount/notes, or issue reporters/admins to approve or decline sponsorships.",
)
def update_sponsorship(
    sponsorship_id: uuid.UUID,
    sponsorship_in: SponsorshipUpdate,
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    return sponsorship_service.update_sponsorship(
        db=db,
        sponsorship_id=sponsorship_id,
        sponsorship_update=sponsorship_in,
        current_profile=current_profile,
    )
