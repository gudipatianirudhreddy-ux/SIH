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

    payload = {"name": "Alice Johnson", "role": "student"}
    response = client.post("/profiles", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == user_id
    assert data["name"] == "Alice Johnson"
    assert data["role"] == "student"
    assert "created_at" in data

    # Verify GET /profiles/me now returns the created profile
    get_res = client.get("/profiles/me")
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["name"] == "Alice Johnson"


def test_create_profile_roles(client):
    for role in ["citizen", "student", "industry"]:
        user_id = str(uuid.uuid4())
        app.dependency_overrides[get_current_user] = lambda u=user_id: MockUser(user_id=u)

        response = client.post("/profiles", json={"name": f"User {role}", "role": role})
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["role"] == role


def test_create_profile_invalid_role(client):
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    payload = {"name": "Invalid User", "role": "superadmin"}
    response = client.post("/profiles", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_profile_already_exists(client):
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    payload = {"name": "First Creation", "role": "citizen"}
    res1 = client.post("/profiles", json=payload)
    assert res1.status_code == status.HTTP_201_CREATED

    res2 = client.post("/profiles", json=payload)
    assert res2.status_code == status.HTTP_409_CONFLICT
    assert res2.json()["detail"] == "Profile already exists for this user"


def test_update_profile_patch_and_put(client):
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    # Initial creation
    create_res = client.post("/profiles", json={"name": "Bob", "role": "student"})
    assert create_res.status_code == status.HTTP_201_CREATED

    # PATCH name only
    patch_res = client.patch("/profiles/me", json={"name": "Bob Builder"})
    assert patch_res.status_code == status.HTTP_200_OK
    assert patch_res.json()["name"] == "Bob Builder"
    assert patch_res.json()["role"] == "student"

    # PUT role only
    put_res = client.put("/profiles/me", json={"role": "industry"})
    assert put_res.status_code == status.HTTP_200_OK
    assert put_res.json()["name"] == "Bob Builder"
    assert put_res.json()["role"] == "industry"


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
    res1 = client.post("/profiles", json={"name": "User One", "role": "citizen"})
    assert res1.status_code == status.HTTP_201_CREATED

    # User 2 checks profile -> should be 404
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user2_id)
    res2 = client.get("/profiles/me")
    assert res2.status_code == status.HTTP_404_NOT_FOUND

    # User 2 creates profile
    res2_create = client.post("/profiles", json={"name": "User Two", "role": "industry"})
    assert res2_create.status_code == status.HTTP_201_CREATED

    # Verify User 1 profile was untouched
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user1_id)
    res1_check = client.get("/profiles/me")
    assert res1_check.status_code == status.HTTP_200_OK
    assert res1_check.json()["name"] == "User One"
    assert res1_check.json()["role"] == "citizen"
