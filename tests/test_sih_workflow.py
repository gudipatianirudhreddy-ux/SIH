import uuid
from fastapi import status

from app.auth import get_current_user
from app.main import app
from app.models.profile import Profile
from tests.conftest import MockUser


def create_user_with_role(client, db_session, role: str, name: str = "Test User") -> str:
    """Helper to create a user and corresponding database profile."""
    user_id = str(uuid.uuid4())
    user_uuid = uuid.UUID(user_id)
    profile = Profile(id=user_uuid, name=name, role=role)
    db_session.add(profile)
    db_session.commit()
    return user_id


# ==============================================================================
# 1. Authenticated user creates issue
# ==============================================================================
def test_authenticated_user_creates_issue(client, db_session):
    user_id = create_user_with_role(client, db_session, role="citizen", name="John Doe")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    payload = {
        "title": "Broken Streetlight on 5th Main",
        "description": "The streetlight has been flickering and completely off for two nights.",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "address": "5th Main, Bengaluru",
        "media_urls": ["https://example.com/images/streetlight_broken.jpg"],
    }
    response = client.post("/issues", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["reporter_id"] == user_id
    assert data["latitude"] == 12.9716
    assert data["longitude"] == 77.5946
    assert len(data["media"]) == 1
    # Auto-ML classification check
    assert data["category"] is not None
    assert data["status"] in ["AI_CLASSIFIED", "REPORTED"]


# ==============================================================================
# 2. Unauthenticated user cannot create issue
# ==============================================================================
def test_unauthenticated_user_cannot_create_issue(client):
    # Ensure no auth override
    app.dependency_overrides.pop(get_current_user, None)

    payload = {
        "title": "Unauthorized Issue",
        "description": "Should fail because user is not authenticated",
    }
    response = client.post("/issues", json=payload)
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


# ==============================================================================
# 3. User retrieves issues (with pagination and filters)
# ==============================================================================
def test_user_retrieves_issues(client, db_session):
    user_id = create_user_with_role(client, db_session, role="citizen")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    # Create two issues
    client.post(
        "/issues",
        json={
            "title": "Issue One Water Leakage",
            "description": "Drinking water pipe burst",
            "category": "Water Supply & Drainage",
            "latitude": 13.0,
            "longitude": 77.0,
        },
    )
    client.post(
        "/issues",
        json={
            "title": "Issue Two Road Pothole",
            "description": "Huge pothole causing traffic",
            "category": "Roads & Potholes",
            "latitude": 14.0,
            "longitude": 78.0,
        },
    )

    # List all
    res = client.get("/issues")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2

    # Filter by category
    filter_res = client.get("/issues", params={"category": "Water Supply & Drainage"})
    assert filter_res.status_code == status.HTTP_200_OK
    filter_data = filter_res.json()
    assert filter_data["total"] == 1
    assert filter_data["items"][0]["category"] == "Water Supply & Drainage"


# ==============================================================================
# 4. User retrieves specific issue
# ==============================================================================
def test_user_retrieves_specific_issue(client, db_session):
    user_id = create_user_with_role(client, db_session, role="citizen")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    create_res = client.post(
        "/issues",
        json={
            "title": "Specific Issue Title",
            "description": "Detailed description for retrieval test",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "address": "New Delhi",
        },
    )
    assert create_res.status_code == status.HTTP_201_CREATED
    issue_id = create_res.json()["id"]

    # Retrieve issue by ID
    get_res = client.get(f"/issues/{issue_id}")
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["id"] == issue_id
    assert get_res.json()["title"] == "Specific Issue Title"


def test_retrieve_nonexistent_issue(client):
    random_id = str(uuid.uuid4())
    res = client.get(f"/issues/{random_id}")
    assert res.status_code == status.HTTP_404_NOT_FOUND


# ==============================================================================
# 5. Student creates solution
# ==============================================================================
def test_student_creates_solution(client, db_session):
    # Reporter creates issue
    citizen_id = create_user_with_role(client, db_session, role="citizen")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    issue_res = client.post(
        "/issues",
        json={"title": "Drainage Overflow", "description": "Needs engineering solution"},
    )
    issue_id = issue_res.json()["id"]

    # Student creates solution
    student_id = create_user_with_role(client, db_session, role="student", name="Student Alice")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)

    solution_payload = {
        "title": "Automated Sump Pump & Filtration Unit",
        "description": "IoT-based flood prevention system with real-time level sensing",
        "pdf_url": "https://example.com/docs/sump_solution_spec.pdf",
        "prototype_url": "https://github.com/student/iot-sump-pump",
    }
    sol_res = client.post(f"/issues/{issue_id}/solutions", json=solution_payload)
    assert sol_res.status_code == status.HTTP_201_CREATED
    sol_data = sol_res.json()
    assert sol_data["student_id"] == student_id
    assert sol_data["issue_id"] == issue_id
    assert sol_data["status"] == "SUBMITTED"
    assert sol_data["title"] == solution_payload["title"]

    # Verify issue status transitioned to SOLUTION_SUBMITTED
    updated_issue_res = client.get(f"/issues/{issue_id}")
    assert updated_issue_res.json()["status"] == "SOLUTION_SUBMITTED"


# ==============================================================================
# 6. Non-student cannot create solution
# ==============================================================================
def test_non_student_cannot_create_solution(client, db_session):
    citizen_id = create_user_with_role(client, db_session, role="citizen")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    issue_res = client.post(
        "/issues",
        json={"title": "Pothole Problem", "description": "Needs road repair"},
    )
    issue_id = issue_res.json()["id"]

    # Citizen attempts to submit a solution -> forbidden
    sol_payload = {
        "title": "Citizen proposal",
        "description": "Trying to submit as citizen",
    }
    sol_res = client.post(f"/issues/{issue_id}/solutions", json=sol_payload)
    assert sol_res.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# 7. Industry can review solution
# ==============================================================================
def test_industry_can_review_solution(client, db_session):
    # Setup issue & solution
    citizen_id = create_user_with_role(client, db_session, role="citizen")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    issue_res = client.post(
        "/issues",
        json={"title": "Solar Lighting Problem", "description": "Need low cost solar"},
    )
    issue_id = issue_res.json()["id"]

    student_id = create_user_with_role(client, db_session, role="student")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    sol_res = client.post(
        f"/issues/{issue_id}/solutions",
        json={
            "title": "Solar LED Grid",
            "description": "High efficiency solar panel and LED lamp",
        },
    )
    solution_id = sol_res.json()["id"]

    # Industry review (support "industrialist" as per existing UserRole)
    industry_id = create_user_with_role(client, db_session, role="industrialist", name="Bosch Mentor")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industry_id)

    review_payload = {
        "rating": 5,
        "feedback": "Excellent technical feasibility. Recommended for pilot production.",
    }
    rev_res = client.post(f"/solutions/{solution_id}/reviews", json=review_payload)
    assert rev_res.status_code == status.HTTP_201_CREATED
    rev_data = rev_res.json()
    assert rev_data["reviewer_id"] == industry_id
    assert rev_data["rating"] == 5
    assert rev_data["feedback"] == review_payload["feedback"]

    # Verify reviews listing
    get_revs = client.get(f"/solutions/{solution_id}/reviews")
    assert get_revs.status_code == status.HTTP_200_OK
    assert len(get_revs.json()) == 1


# ==============================================================================
# 8. Student/Citizen cannot create industry review
# ==============================================================================
def test_student_and_citizen_cannot_create_industry_review(client, db_session):
    citizen_id = create_user_with_role(client, db_session, role="citizen")
    student_id = create_user_with_role(client, db_session, role="student")

    # Create issue and solution
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    issue_res = client.post("/issues", json={"title": "Issue X", "description": "Desc X"})
    issue_id = issue_res.json()["id"]

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    sol_res = client.post(
        f"/issues/{issue_id}/solutions",
        json={"title": "Sol X", "description": "Desc Sol X"},
    )
    solution_id = sol_res.json()["id"]

    # Student attempts review -> forbidden
    rev_res_student = client.post(
        f"/solutions/{solution_id}/reviews",
        json={"rating": 4, "feedback": "Self-review attempt"},
    )
    assert rev_res_student.status_code == status.HTTP_403_FORBIDDEN

    # Citizen attempts review -> forbidden
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    rev_res_citizen = client.post(
        f"/solutions/{solution_id}/reviews",
        json={"rating": 3, "feedback": "Citizen review attempt"},
    )
    assert rev_res_citizen.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# 9. Issue ownership / authorization checks
# ==============================================================================
def test_issue_ownership_authorization(client, db_session):
    user1_id = create_user_with_role(client, db_session, role="citizen", name="User One")
    user2_id = create_user_with_role(client, db_session, role="citizen", name="User Two")

    # User 1 creates issue
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user1_id)
    issue_res = client.post(
        "/issues",
        json={"title": "Original Title", "description": "Original Description"},
    )
    issue_id = issue_res.json()["id"]

    # User 2 attempts to patch User 1's issue -> forbidden
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user2_id)
    patch_res = client.patch(
        f"/issues/{issue_id}",
        json={"title": "Malicious Overwrite"},
    )
    assert patch_res.status_code == status.HTTP_403_FORBIDDEN

    # User 2 attempts to delete User 1's issue -> forbidden
    del_res = client.delete(f"/issues/{issue_id}")
    assert del_res.status_code == status.HTTP_403_FORBIDDEN

    # User 1 updates their own issue -> success
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user1_id)
    owner_patch = client.patch(
        f"/issues/{issue_id}",
        json={"title": "Updated Title by Reporter"},
    )
    assert owner_patch.status_code == status.HTTP_200_OK
    assert owner_patch.json()["title"] == "Updated Title by Reporter"

    # User 1 deletes their own issue -> success
    owner_del = client.delete(f"/issues/{issue_id}")
    assert owner_del.status_code == status.HTTP_204_NO_CONTENT


# ==============================================================================
# 10. Basic validation for coordinates
# ==============================================================================
def test_coordinate_validation(client, db_session):
    user_id = create_user_with_role(client, db_session, role="citizen")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    # Latitude out of bounds (> 90)
    bad_lat = {
        "title": "Invalid Latitude Issue",
        "description": "Coordinate out of range",
        "latitude": 95.0,
        "longitude": 77.0,
    }
    res_lat = client.post("/issues", json=bad_lat)
    assert res_lat.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Longitude out of bounds (< -180)
    bad_lon = {
        "title": "Invalid Longitude Issue",
        "description": "Coordinate out of range",
        "latitude": 12.0,
        "longitude": -190.0,
    }
    res_lon = client.post("/issues", json=bad_lon)
    assert res_lon.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Valid coordinates edge test
    valid_coords = {
        "title": "Valid Edge Coordinates",
        "description": "Valid coordinates test",
        "latitude": -90.0,
        "longitude": 180.0,
    }
    res_valid = client.post("/issues", json=valid_coords)
    assert res_valid.status_code == status.HTTP_201_CREATED
    assert res_valid.json()["latitude"] == -90.0
    assert res_valid.json()["longitude"] == 180.0


# ==============================================================================
# 11. Media attachment and auto-classification
# ==============================================================================
def test_attach_media_and_classification(client, db_session):
    citizen_id = create_user_with_role(client, db_session, role="citizen")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)

    # Create issue without initial category or media
    issue_res = client.post(
        "/issues",
        json={"title": "Road Problem", "description": "Big hole in road"},
    )
    issue_id = issue_res.json()["id"]
    assert issue_res.json()["category"] is None

    # Attach image media
    media_res = client.post(
        f"/issues/{issue_id}/media",
        json={"media_url": "https://storage.sih.org/pothole_asphalt_hazard.jpg", "media_type": "image"},
    )
    assert media_res.status_code == status.HTTP_201_CREATED
    media_data = media_res.json()
    assert media_data["issue_id"] == issue_id
    assert "pothole" in media_data["media_url"]

    # Verify issue was automatically categorized by ML classifier
    updated_issue = client.get(f"/issues/{issue_id}").json()
    assert updated_issue["category"] == "Roads & Potholes"
    assert updated_issue["status"] == "AI_CLASSIFIED"
    assert updated_issue["category_confidence"] is not None


# ==============================================================================
# 12. Solution update ownership rules
# ==============================================================================
def test_solution_update_authorization(client, db_session):
    citizen_id = create_user_with_role(client, db_session, role="citizen")
    student1_id = create_user_with_role(client, db_session, role="student", name="Student 1")
    student2_id = create_user_with_role(client, db_session, role="student", name="Student 2")

    # Citizen posts issue
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    issue_res = client.post("/issues", json={"title": "Issue Y", "description": "Desc Y"})
    issue_id = issue_res.json()["id"]

    # Student 1 posts solution
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student1_id)
    sol_res = client.post(
        f"/issues/{issue_id}/solutions",
        json={"title": "Original Sol Title", "description": "Original Sol Desc"},
    )
    solution_id = sol_res.json()["id"]

    # Student 2 tries to edit content -> forbidden
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student2_id)
    patch_fail = client.patch(
        f"/solutions/{solution_id}",
        json={"title": "Hijacked Sol Title"},
    )
    assert patch_fail.status_code == status.HTTP_403_FORBIDDEN

    # Student 1 updates their own content -> success
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student1_id)
    patch_ok = client.patch(
        f"/solutions/{solution_id}",
        json={"title": "Refined Sol Title", "prototype_url": "https://demo.example.com"},
    )
    assert patch_ok.status_code == status.HTTP_200_OK
    assert patch_ok.json()["title"] == "Refined Sol Title"
    assert patch_ok.json()["prototype_url"] == "https://demo.example.com"

