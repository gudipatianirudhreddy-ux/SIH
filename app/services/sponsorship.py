from typing import List, Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import SponsorshipStatus
from app.models.issue import Issue
from app.models.profile import Profile
from app.models.sponsorship import Sponsorship
from app.schemas.sponsorship import SponsorshipCreate, SponsorshipUpdate


def create_sponsorship(
    db: Session,
    issue_id: uuid.UUID,
    industrialist_profile: Profile,
    sponsorship_in: SponsorshipCreate,
) -> Sponsorship:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    if sponsorship_in.amount < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sponsorship amount must be non-negative",
        )

    db_sponsorship = Sponsorship(
        issue_id=issue_id,
        industrialist_id=industrialist_profile.id,
        amount=sponsorship_in.amount,
        message=sponsorship_in.message,
        status=SponsorshipStatus.PLEDGED.value,
    )
    db.add(db_sponsorship)
    db.commit()
    db.refresh(db_sponsorship)
    return db_sponsorship


def get_sponsorship_by_id(db: Session, sponsorship_id: uuid.UUID) -> Optional[Sponsorship]:
    return db.query(Sponsorship).filter(Sponsorship.id == sponsorship_id).first()


def list_sponsorships_for_issue(
    db: Session,
    issue_id: uuid.UUID,
    current_profile: Profile,
) -> List[Sponsorship]:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    user_role = (current_profile.role or "").lower()
    is_reporter = issue.reporter_id == current_profile.id
    is_admin = user_role == "admin"
    is_industry = user_role in ("industry", "industrialist")

    # Visible to issue reporter, industry members, and admins
    if not (is_reporter or is_admin or is_industry):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view sponsorships for this issue",
        )

    return (
        db.query(Sponsorship)
        .filter(Sponsorship.issue_id == issue_id)
        .order_by(Sponsorship.created_at.desc())
        .all()
    )


def update_sponsorship(
    db: Session,
    sponsorship_id: uuid.UUID,
    sponsorship_update: SponsorshipUpdate,
    current_profile: Profile,
) -> Sponsorship:
    sponsorship = get_sponsorship_by_id(db, sponsorship_id)
    if not sponsorship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sponsorship not found",
        )

    issue = db.query(Issue).filter(Issue.id == sponsorship.issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated issue not found",
        )

    user_role = (current_profile.role or "").lower()
    is_sponsor_owner = sponsorship.industrialist_id == current_profile.id
    is_reporter = issue.reporter_id == current_profile.id
    is_admin = user_role == "admin"

    if sponsorship_update.amount is not None:
        if sponsorship_update.amount < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sponsorship amount must be non-negative",
            )
        # Only sponsor owner or admin can update amount
        if not (is_sponsor_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the sponsor or admin can modify sponsorship amount",
            )
        sponsorship.amount = sponsorship_update.amount

    if sponsorship_update.message is not None:
        if not (is_sponsor_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the sponsor or admin can modify sponsorship message",
            )
        sponsorship.message = sponsorship_update.message

    if sponsorship_update.status is not None:
        new_status = sponsorship_update.status
        # Status approval/decline is permitted for issue reporter or admin
        if new_status in (SponsorshipStatus.APPROVED, SponsorshipStatus.DECLINED):
            if not (is_reporter or is_admin):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the issue reporter or admin can approve/decline sponsorship",
                )
        elif new_status == SponsorshipStatus.COMPLETED:
            if not (is_sponsor_owner or is_reporter or is_admin):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to mark this sponsorship as completed",
                )
        sponsorship.status = new_status.value

    db.commit()
    db.refresh(sponsorship)
    return sponsorship
