import uuid
import pytest
from fastapi import status

from app.auth import get_current_user
from app.main import app
from app.models.enums import IssueStatus
from app.models.issue import Issue
from tests.conftest import MockClassifier, MockUser


def _create_user(client, role: str = "citizen") -> str:
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)
    res = client.post("/profiles/me", json={"name": "ML Tester", "role": role})
    assert res.status_code == status.HTTP_201_CREATED
    return user_id


def test_issue_with_image_triggers_classification(client, db_session):
    """An issue reported with an image URL triggers ML classification and stores category/confidence."""
    user_id = _create_user(client)
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    payload = {
        "title": "Severe road damage with deep asphalt crack",
        "description": "Large pothole in the middle lane causing vehicular slowdown",
        "media_urls": ["https://storage.supabase.co/sih-bucket/pothole_cracked_road.jpg"],
    }
    response = client.post("/issues", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # Verify classification results
    assert data["status"] == IssueStatus.AI_CLASSIFIED.value
    assert data["category"] == "Roads & Potholes"
    assert data["category_confidence"] == pytest.approx(0.94)

    # Verify persisted in database
    issue_record = db_session.query(Issue).filter(Issue.id == uuid.UUID(data["id"])).first()
    assert issue_record is not None
    assert issue_record.status == IssueStatus.AI_CLASSIFIED.value
    assert issue_record.category == "Roads & Potholes"
    assert issue_record.category_confidence == pytest.approx(0.94)


def test_issue_without_image_does_not_trigger_classification(client):
    """An issue reported without media remains in REPORTED status without category confidence."""
    user_id = _create_user(client)
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    payload = {
        "title": "Noise Complaint",
        "description": "Loud construction noise late at night",
    }
    response = client.post("/issues", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["status"] == IssueStatus.REPORTED.value
    assert data["category_confidence"] is None


def test_adding_media_to_uncategorized_issue_triggers_classification(client, db_session):
    """Attaching media to an issue that lacks category triggers classifier and transitions to AI_CLASSIFIED."""
    user_id = _create_user(client)
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    # 1. Create issue without media or category
    create_res = client.post(
        "/issues",
        json={"title": "Accumulation of domestic waste", "description": "Pile of trash near market"},
    )
    assert create_res.status_code == status.HTTP_201_CREATED
    issue_id = create_res.json()["id"]
    assert create_res.json()["status"] == IssueStatus.REPORTED.value

    # 2. Add media with garbage keyword
    media_res = client.post(
        f"/issues/{issue_id}/media",
        json={
            "media_url": "https://storage.supabase.co/sih-bucket/overflowing_garbage_dump.jpg",
            "media_type": "image",
        },
    )
    assert media_res.status_code == status.HTTP_201_CREATED

    # 3. Verify issue is now classified
    issue_res = client.get(f"/issues/{issue_id}")
    assert issue_res.status_code == status.HTTP_200_OK
    data = issue_res.json()
    assert data["status"] == IssueStatus.AI_CLASSIFIED.value
    assert data["category"] == "Garbage & Waste Management"
    assert data["category_confidence"] == pytest.approx(0.92)
