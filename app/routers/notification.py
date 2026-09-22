import uuid
from typing import Dict

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth import require_authenticated_user
from app.database import get_db
from app.models.profile import Profile
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services import notification as notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "/me",
    response_model=NotificationListResponse,
    summary="Get authenticated user's notifications",
    description="Returns the paginated notifications for the authenticated user, ordered newest first, with optional unread_only filtering.",
)
def get_my_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    unread_only: bool = Query(False, description="Filter to only unread notifications"),
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    items, total, unread_count = notification_service.get_user_notifications(
        db=db,
        user_id=current_profile.id,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
    )
    return NotificationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        unread_count=unread_count,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count",
    description="Returns the total count of unread notifications for the authenticated user.",
)
def get_unread_count(
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    count = notification_service.get_unread_count(db=db, user_id=current_profile.id)
    return UnreadCountResponse(count=count)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark single notification as read",
    description="Marks a specific notification as read. Users can only modify their own notifications.",
)
def mark_as_read(
    notification_id: uuid.UUID,
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    return notification_service.mark_notification_as_read(
        db=db,
        notification_id=notification_id,
        user_id=current_profile.id,
    )


@router.patch(
    "/read-all",
    summary="Mark all notifications as read",
    description="Marks all unread notifications belonging to the authenticated user as read.",
)
def mark_all_as_read(
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> Dict[str, object]:
    count = notification_service.mark_all_notifications_as_read(
        db=db,
        user_id=current_profile.id,
    )
    return {"message": "All notifications marked as read", "count": count}
