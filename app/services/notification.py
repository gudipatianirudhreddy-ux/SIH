from datetime import datetime, timezone
import re
from typing import List, Optional, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import NotificationType
from app.models.interest import IndustrialistInterest, StudentInterest
from app.models.issue import Issue
from app.models.notification import Notification


def create_notification(
    db: Session,
    recipient_id: uuid.UUID,
    notification_type: str,
    title: str,
    message: str,
    issue_id: Optional[uuid.UUID] = None,
    application_id: Optional[uuid.UUID] = None,
    collaboration_id: Optional[uuid.UUID] = None,
) -> Notification:
    """Creates an in-app notification with duplicate prevention."""
    # Normalize notification type to string value if an Enum was passed
    if hasattr(notification_type, "value"):
        type_str = notification_type.value
    else:
        type_str = str(notification_type)

    # Duplicate check: check if the exact same notification was already created
    existing_query = db.query(Notification).filter(
        Notification.recipient_id == recipient_id,
        Notification.type == type_str,
        Notification.title == title,
    )
    if issue_id is not None:
        existing_query = existing_query.filter(Notification.related_issue_id == issue_id)
    if application_id is not None:
        existing_query = existing_query.filter(Notification.related_application_id == application_id)
    if collaboration_id is not None:
        existing_query = existing_query.filter(Notification.related_collaboration_id == collaboration_id)

    existing = existing_query.first()
    if existing:
        return existing

    notification = Notification(
        recipient_id=recipient_id,
        type=type_str,
        title=title,
        message=message,
        related_issue_id=issue_id,
        related_application_id=application_id,
        related_collaboration_id=collaboration_id,
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_user_notifications(
    db: Session,
    user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
) -> Tuple[List[Notification], int, int]:
    """Returns paginated notifications for the authenticated user along with total count and unread count."""
    base_query = db.query(Notification).filter(Notification.recipient_id == user_id)
    unread_count = base_query.filter(Notification.is_read == False).count()

    query = base_query
    if unread_only:
        query = query.filter(Notification.is_read == False)

    total = query.count()
    items = (
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total, unread_count


def get_unread_count(db: Session, user_id: uuid.UUID) -> int:
    """Returns the count of unread notifications for a user."""
    return db.query(Notification).filter(
        Notification.recipient_id == user_id,
        Notification.is_read == False,
    ).count()


def mark_notification_as_read(
    db: Session,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Notification:
    """Marks a single notification as read, ensuring strict ownership authorization."""
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    if notification.recipient_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this notification",
        )

    if not notification.is_read:
        notification.is_read = True
        db.commit()
        db.refresh(notification)

    return notification


def mark_all_notifications_as_read(
    db: Session,
    user_id: uuid.UUID,
) -> int:
    """Marks all unread notifications for a user as read."""
    updated = (
        db.query(Notification)
        .filter(
            Notification.recipient_id == user_id,
            Notification.is_read == False,
        )
        .update({"is_read": True}, synchronize_session="fetch")
    )
    db.commit()
    return updated


def _matches_keywords(text_to_search: str, keywords_str: Optional[str]) -> bool:
    """Helper to check if any comma-separated or tokenized keyword appears in the target text."""
    if not keywords_str:
        return False
    # Split keywords by commas, semicolons, or newlines
    tokens = [t.strip().lower() for t in re.split(r"[,;\n]+", keywords_str) if t.strip()]
    target = text_to_search.lower()
    return any(t in target for t in tokens)


def notify_interest_matches_for_issue(db: Session, issue: Issue) -> None:
    """Checks industrialist and student interests against a new or verified issue and creates INTEREST_MATCH notifications."""
    issue_text = f"{issue.title or ''} {issue.description or ''} {issue.category or ''}"

    # 1. Industrialist interests
    industrialists = db.query(IndustrialistInterest).all()
    for ind in industrialists:
        if ind.profile_id == issue.reporter_id:
            continue
        domain_match = ind.industry_domain and ind.industry_domain.strip().lower() in issue_text.lower()
        focus_match = _matches_keywords(issue_text, ind.focus_areas)
        if domain_match or focus_match:
            create_notification(
                db=db,
                recipient_id=ind.profile_id,
                notification_type=NotificationType.INTEREST_MATCH,
                title="Societal Issue Matches Your Interests",
                message=f"A new issue '{issue.title}' matching your focus area ({issue.category or 'Community'}) is available.",
                issue_id=issue.id,
            )

    # 2. Student interests
    students = db.query(StudentInterest).all()
    for stu in students:
        if stu.profile_id == issue.reporter_id:
            continue
        area_match = _matches_keywords(issue_text, stu.interest_areas)
        skill_match = _matches_keywords(issue_text, stu.skills)
        if area_match or skill_match:
            create_notification(
                db=db,
                recipient_id=stu.profile_id,
                notification_type=NotificationType.INTEREST_MATCH,
                title="Problem Matches Your Skills & Interests",
                message=f"An issue '{issue.title}' matching your skills and interests is open for student applications.",
                issue_id=issue.id,
            )
