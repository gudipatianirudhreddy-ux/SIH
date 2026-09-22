from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import IssueStatus
from app.models.issue import Issue, IssueMedia
from app.models.profile import Profile
from app.schemas.issue import IssueCreate, IssueUpdate
from app.services.ml_classifier import IssueClassifier, get_issue_classifier
from app.services.profile import add_points
from app.services.status_transition import validate_issue_status_transition



def create_issue(
    db: Session,
    reporter_id: uuid.UUID,
    issue_data: IssueCreate,
    classifier: Optional[IssueClassifier] = None,
) -> Issue:
    """Create a new societal issue and triggers ML classification if media is provided."""
    classifier = classifier or get_issue_classifier()

    db_issue = Issue(
        reporter_id=reporter_id,
        title=issue_data.title,
        description=issue_data.description,
        category=issue_data.category,
        priority=issue_data.priority.value if issue_data.priority else None,
        latitude=issue_data.latitude,
        longitude=issue_data.longitude,
        address=issue_data.address,
        status=IssueStatus.REPORTED.value,
    )
    db.add(db_issue)
    db.flush()

    # Attach initial media if provided
    first_image_url = None
    if issue_data.media_urls:
        for url in issue_data.media_urls:
            media = IssueMedia(
                issue_id=db_issue.id,
                media_url=url,
                media_type="image",
            )
            db.add(media)
            if not first_image_url:
                first_image_url = url

    # ML Classification step
    if first_image_url:
        classification = classifier.classify(first_image_url)
        if not db_issue.category and classification.get("category"):
            db_issue.category = classification["category"]
        db_issue.category_confidence = classification.get("confidence")
        db_issue.status = IssueStatus.AI_CLASSIFIED.value

    db.commit()
    reporter = db.query(Profile).filter(Profile.id == reporter_id).first()
    if reporter and (reporter.role or "").lower() == "citizen":
        add_points(db, reporter_id, 10, "ISSUE_REPORTED", db_issue.id)
    db.refresh(db_issue)
    return db_issue


def get_issue_by_id(db: Session, issue_id: uuid.UUID) -> Optional[Issue]:
    return db.query(Issue).filter(Issue.id == issue_id).first()


def list_issues(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    category: Optional[str] = None,
    status: Optional[str] = None,
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None,
) -> Tuple[List[Issue], int]:
    query = db.query(Issue)

    if category:
        query = query.filter(Issue.category.ilike(f"%{category.strip()}%"))
    if status:
        query = query.filter(func.lower(Issue.status) == status.strip().lower())
    if min_lat is not None:
        query = query.filter(Issue.latitude >= min_lat)
    if max_lat is not None:
        query = query.filter(Issue.latitude <= max_lat)
    if min_lon is not None:
        query = query.filter(Issue.longitude >= min_lon)
    if max_lon is not None:
        query = query.filter(Issue.longitude <= max_lon)

    total = query.count()
    items = (
        query.order_by(Issue.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def update_issue(
    db: Session,
    issue: Issue,
    issue_update: IssueUpdate,
    profile: Optional[Profile] = None,
) -> Issue:
    if issue_update.status is not None:
        validate_issue_status_transition(
            issue=issue,
            new_status=issue_update.status.value,
            profile=profile,
        )
        issue.status = issue_update.status.value

    if issue_update.title is not None:
        issue.title = issue_update.title
    if issue_update.description is not None:
        issue.description = issue_update.description
    if issue_update.category is not None:
        issue.category = issue_update.category
    if issue_update.priority is not None:
        issue.priority = issue_update.priority.value
    if issue_update.latitude is not None:
        issue.latitude = issue_update.latitude
    if issue_update.longitude is not None:
        issue.longitude = issue_update.longitude
    if issue_update.address is not None:
        issue.address = issue_update.address

    db.commit()
    db.refresh(issue)
    return issue


def list_reported_issues(
    db: Session,
    reporter_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Issue], int]:
    query = db.query(Issue).filter(Issue.reporter_id == reporter_id)
    total = query.count()
    items = (
        query.order_by(Issue.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def list_assigned_issues(
    db: Session,
    student_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Issue], int]:
    query = db.query(Issue).filter(Issue.assigned_student_id == student_id)
    total = query.count()
    items = (
        query.order_by(Issue.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def delete_issue(db: Session, issue: Issue) -> None:
    db.delete(issue)
    db.commit()



def add_media_to_issue(
    db: Session,
    issue: Issue,
    media_url: str,
    media_type: str = "image",
    classifier: Optional[IssueClassifier] = None,
) -> IssueMedia:
    classifier = classifier or get_issue_classifier()
    media = IssueMedia(
        issue_id=issue.id,
        media_url=media_url,
        media_type=media_type,
    )
    db.add(media)

    # If issue has no category, run classifier on the new image
    if media_type == "image" and not issue.category:
        classification = classifier.classify(media_url)
        issue.category = classification.get("category")
        issue.category_confidence = classification.get("confidence")
        if issue.status == IssueStatus.REPORTED.value:
            issue.status = IssueStatus.AI_CLASSIFIED.value

    db.commit()
    db.refresh(media)
    db.refresh(issue)
    return media
