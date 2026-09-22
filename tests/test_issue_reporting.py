import uuid
import pytest
from fastapi import status

from app.auth import get_current_user
from app.main import app
from app.models.issue import Issue
from app.models.profile import Profile
from tests.conftest import MockUser


def _create_user_with_role(client, role: str, name: str) -> str:
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)
    res = client.post("/profiles/me", json={"name": name, "role": role})
    assert res.status_code == status.HTTP_201_CREATED
    return user_id


@pytest.mark.parametrize("role", ["citizen", "student", "industrialist"])
def test_authenticated_roles_can_post_issues(client, role):
    """Citizen, Student, and Industrialist can all successfully POST /issues."""
    user_id = _create_user_with_role(client, role=role, name=f"Issue Creator {role}")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    payload = {
        "title": f"Community Park Lighting by {role}",
        "description": "Streetlights not functioning after 7 PM in Sector 4 park",
        "category": "Electricity & Street Lighting",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "address": "Sector 4 Community Park",
    }
    response = client.post("/issues", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["reporter_id"] == user_id
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["category"] == payload["category"]


def test_unauthenticated_user_cannot_post_issues(client):
    """Unauthenticated request to POST /issues is rejected with 401 or 403."""
    app.dependency_overrides.clear()
    payload = {
        "title": "Unauthorized Issue",
        "description": "This request should be rejected without auth",
    }
    response = client.post("/issues", json=payload)
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


def test_reporter_id_cannot_be_spoofed_in_request_data(client, db_session):
    """reporter_id is strictly derived from authenticated profile and cannot be spoofed via request payload."""
    legit_user_id = _create_user_with_role(client, role="citizen", name="Legit User")
    victim_user_id = _create_user_with_role(client, role="citizen", name="Victim User")

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=legit_user_id)

    # Attempt to spoof reporter_id to victim_user_id
    malicious_payload = {
        "title": "Spoofed Issue Title",
        "description": "Trying to impersonate victim in reporter_id",
        "reporter_id": victim_user_id,  # Spoof attempt
    }
    response = client.post("/issues", json=malicious_payload)
    assert response.status_code == status.HTTP_201_CREATED
    issue_data = response.json()

    # Verify reporter_id in response is the authenticated user, NOT the victim
    assert issue_data["reporter_id"] == legit_user_id
    assert issue_data["reporter_id"] != victim_user_id

    # Verify directly in DB
    db_issue = db_session.query(Issue).filter(Issue.id == uuid.UUID(issue_data["id"])).first()
    assert str(db_issue.reporter_id) == legit_user_id
    assert str(db_issue.reporter_id) != victim_user_id


def test_created_issue_associated_with_correct_reporter_and_list_reported(client):
    """Each created issue is associated with correct reporter and retrieved via /issues/me/reported."""
    user1_id = _create_user_with_role(client, role="student", name="Student Reporter")
    user2_id = _create_user_with_role(client, role="industrialist", name="Industry Reporter")

    # User 1 posts 2 issues
    app.dependency_overrides[get_current_user] = lambda: MockUser(user1_id)
    res1_a = client.post("/issues", json={"title": "Issue 1A", "description": "Desc 1A"})
    res1_b = client.post("/issues", json={"title": "Issue 1B", "description": "Desc 1B"})
    assert res1_a.status_code == status.HTTP_201_CREATED
    assert res1_b.status_code == status.HTTP_201_CREATED

    # User 2 posts 1 issue
    app.dependency_overrides[get_current_user] = lambda: MockUser(user2_id)
    res2_a = client.post("/issues", json={"title": "Issue 2A", "description": "Desc 2A"})
    assert res2_a.status_code == status.HTTP_201_CREATED

    # User 1 queries /issues/me/reported -> sees exactly 2 issues belonging to User 1
    app.dependency_overrides[get_current_user] = lambda: MockUser(user1_id)
    rep1 = client.get("/issues/me/reported")
    assert rep1.status_code == status.HTTP_200_OK
    rep1_data = rep1.json()
    assert rep1_data["total"] == 2
    for item in rep1_data["items"]:
        assert item["reporter_id"] == user1_id

    # User 2 queries /issues/me/reported -> sees exactly 1 issue belonging to User 2
    app.dependency_overrides[get_current_user] = lambda: MockUser(user2_id)
    rep2 = client.get("/issues/me/reported")
    assert rep2.status_code == status.HTTP_200_OK
    rep2_data = rep2.json()
    assert rep2_data["total"] == 1
    assert rep2_data["items"][0]["reporter_id"] == user2_id


@pytest.mark.parametrize("role", ["citizen", "student", "industrialist"])
def test_all_three_roles_receive_issue_reporting_reward(client, role):
    """All 3 stakeholder roles receive +10 points reward on POST /issues."""
    user_id = _create_user_with_role(client, role=role, name=f"Rewardee {role}")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    # Initial points = 50
    assert client.get("/points/me").json()["points"] == 50

    # Post issue
    res = client.post("/issues", json={"title": "Reward Check", "description": "Testing rewards"})
    assert res.status_code == status.HTTP_201_CREATED

    # After posting = 60
    pts_res = client.get("/points/me")
    assert pts_res.json()["points"] == 60
    txs = pts_res.json()["transactions"]
    assert any(t["reason"] == "ISSUE_REPORTED" and t["points"] == 10 for t in txs)
