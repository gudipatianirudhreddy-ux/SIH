import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.collaboration import Collaboration
from app.models.enums import ApplicationStatus, CollaborationStatus, IssueStatus
from app.models.issue import Issue
from app.models.profile import Profile


def select_application_and_create_collaboration(
    db: Session,
    application_id: uuid.UUID,
    industrialist: Profile,
) -> Collaboration:
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    issue = db.query(Issue).filter(Issue.id == application.issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated issue not found")

    if application.status != ApplicationStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending applications can be selected")

    if issue.status != IssueStatus.VERIFIED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only verified issues can start a collaboration")

    existing = db.query(Collaboration).filter(Collaboration.issue_id == issue.id).first()
    if existing and existing.status == CollaborationStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This issue already has an active collaboration")

    collaboration = Collaboration(
        issue_id=issue.id,
        application_id=application.id,
        student_id=application.student_id,
        industrialist_id=industrialist.id,
        status=CollaborationStatus.ACTIVE.value,
    )
    db.add(collaboration)

    application.status = ApplicationStatus.SELECTED.value
    issue.assigned_student_id = application.student_id
    issue.status = IssueStatus.IN_PROGRESS.value

    other_pending = db.query(Application).filter(
        Application.issue_id == issue.id,
        Application.id != application.id,
        Application.status == ApplicationStatus.PENDING.value,
    ).all()
    for other in other_pending:
        other.status = ApplicationStatus.REJECTED.value

    db.commit()
    db.refresh(collaboration)
    return collaboration


def list_my_collaborations(db: Session, profile: Profile):
    role = (profile.role or "").lower()
    query = db.query(Collaboration)
    if role in ("industry", "industrialist"):
        query = query.filter(Collaboration.industrialist_id == profile.id)
    elif role == "student":
        query = query.filter(Collaboration.student_id == profile.id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students and industrialists can view collaborations")
    return query.order_by(Collaboration.created_at.desc()).all()


def get_collaboration(db: Session, collaboration_id: uuid.UUID, profile: Profile) -> Collaboration:
    collaboration = db.query(Collaboration).filter(Collaboration.id == collaboration_id).first()
    if not collaboration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collaboration not found")
    role = (profile.role or "").lower()
    if role != "admin" and profile.id not in (collaboration.student_id, collaboration.industrialist_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not part of this collaboration")
    return collaboration
