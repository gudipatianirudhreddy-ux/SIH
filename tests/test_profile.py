import uuid
from fastapi import status

from app.auth import get_current_user
from app.main import app
from tests.conftest import MockUser


def test_unauthenticated_access(client):
    response = client.get("/profiles/me")
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


def test_get_profile_not_found(client):
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    response = client.get("/profiles/me")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Profile not found"


def test_create_profile_success(client):
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    payload = {
        "name": "Alice Johnson",
        "role": "student",
        "phone_number": "+91 9876543210",
        "avatar_url": "https://example.com/avatar.png",
        "location": "Bengaluru, Karnataka",
    }
    response = client.post("/profiles/me", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == user_id
    assert data["name"] == "Alice Johnson"
    assert data["role"] == "student"
    assert data["phone_number"] == "+91 9876543210"
    assert data["avatar_url"] == "https://example.com/avatar.png"
    assert data["location"] == "Bengaluru, Karnataka"
    assert "created_at" in data
    assert "updated_at" in data

    # Verify GET /profiles/me returns all fields
    get_res = client.get("/profiles/me")
    assert get_res.status_code == status.HTTP_200_OK
    get_data = get_res.json()
    assert get_data["name"] == "Alice Johnson"
    assert get_data["phone_number"] == "+91 9876543210"
    assert get_data["avatar_url"] == "https://example.com/avatar.png"
    assert get_data["location"] == "Bengaluru, Karnataka"
    assert "created_at" in get_data
    assert "updated_at" in get_data


def test_create_profile_optional_fields(client):
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    payload = {"name": "Minimal User", "role": "citizen"}
    response = client.post("/profiles/me", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["phone_number"] is None
    assert data["avatar_url"] is None
    assert data["location"] is None


def test_create_profile_invalid_phone_number(client):
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    # Invalid characters
    payload = {"name": "Bad Phone", "role": "student", "phone_number": "invalid-phone"}
    response = client.post("/profiles/me", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Too short
    payload_short = {"name": "Bad Phone", "role": "student", "phone_number": "123"}
    response_short = client.post("/profiles/me", json=payload_short)
    assert response_short.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_profile_roles(client):
    for role in ["citizen", "student", "industrialist"]:
        user_id = str(uuid.uuid4())
        app.dependency_overrides[get_current_user] = lambda u=user_id: MockUser(user_id=u)

        response = client.post("/profiles/me", json={"name": f"User {role}", "role": role})
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["role"] == role


def test_create_profile_invalid_role(client):
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    payload = {"name": "Invalid User", "role": "industry"}  # Old 'industry' should now fail
    response = client.post("/profiles/me", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_profile_already_exists(client):
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    payload = {"name": "First Creation", "role": "citizen"}
    res1 = client.post("/profiles/me", json=payload)
    assert res1.status_code == status.HTTP_201_CREATED

    res2 = client.post("/profiles/me", json=payload)
    assert res2.status_code == status.HTTP_409_CONFLICT
    assert res2.json()["detail"] == "Profile already exists for this user"


def test_update_profile_patch(client):
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    # Initial creation
    create_res = client.post("/profiles/me", json={"name": "Bob", "role": "student"})
    assert create_res.status_code == status.HTTP_201_CREATED

    # PATCH updates name, avatar_url, location, and phone_number
    patch_res = client.patch(
        "/profiles/me",
        json={
            "name": "Bob Builder",
            "phone_number": "+91 9876543210",
            "avatar_url": "https://example.com/bob.jpg",
            "location": "Mumbai, Maharashtra",
            "role": "industrialist",
        },
    )
    assert patch_res.status_code == status.HTTP_200_OK
    updated_data = patch_res.json()
    assert updated_data["name"] == "Bob Builder"
    assert updated_data["role"] == "industrialist"
    assert updated_data["phone_number"] == "+91 9876543210"
    assert updated_data["avatar_url"] == "https://example.com/bob.jpg"
    assert updated_data["location"] == "Mumbai, Maharashtra"


def test_update_profile_not_found(client):
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    response = client.patch("/profiles/me", json={"name": "Ghost"})
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_user_isolation(client):
    user1_id = str(uuid.uuid4())
    user2_id = str(uuid.uuid4())

    # User 1 creates profile
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user1_id)
    res1 = client.post(
        "/profiles/me",
        json={"name": "User One", "role": "citizen", "phone_number": "+91 11111 11111"},
    )
    assert res1.status_code == status.HTTP_201_CREATED

    # User 2 checks profile -> should be 404
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user2_id)
    res2 = client.get("/profiles/me")
    assert res2.status_code == status.HTTP_404_NOT_FOUND

    # User 2 creates profile
    res2_create = client.post(
        "/profiles/me",
        json={"name": "User Two", "role": "industrialist", "phone_number": "+91 22222 22222"},
    )
    assert res2_create.status_code == status.HTTP_201_CREATED

    # Verify User 1 profile was untouched
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user1_id)
    res1_check = client.get("/profiles/me")
    assert res1_check.status_code == status.HTTP_200_OK
    assert res1_check.json()["name"] == "User One"
    assert res1_check.json()["role"] == "citizen"
    assert res1_check.json()["phone_number"] == "+91 11111 11111"
