from fastapi.testclient import TestClient
import pytest

from core.security import create_access_token
from main import app
from services.user_service import UserService
from settings import get_db


@pytest.fixture
def client(session):
    app.dependency_overrides[get_db] = lambda: session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def auth_headers(user):
    token = create_access_token({"sub": str(user.private_id), "role": user.role.name})
    return {"Authorization": f"Bearer {token}"}


def test_public_registration_cannot_assign_admin_role(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "First Customer",
            "email": "first.customer@gmail.com",
            "password": "secure-test-password",
            "role": "ADMIN",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "CUSTOMER"


def test_user_profile_requires_authentication_and_blocks_other_users(client, session):
    service = UserService(session)
    first = service.create_user(
        email="first@example.test", name="First User", password="test-password"
    )
    second = service.create_user(
        email="second@example.test", name="Second User", password="test-password"
    )

    anonymous = client.get(f"/api/v1/users/{first.public_id}")
    assert anonymous.status_code == 401

    response = client.get(
        f"/api/v1/users/{second.public_id}", headers=auth_headers(first)
    )
    assert response.status_code == 403

    own_profile = client.get(
        f"/api/v1/users/{first.public_id}", headers=auth_headers(first)
    )
    assert own_profile.status_code == 200
    assert own_profile.json()["public_id"] == str(first.public_id)


def test_admin_can_update_another_users_profile(client, session):
    service = UserService(session)
    admin = service.create_user(
        email="admin@example.test", name="Admin User", password="test-password", role="ADMIN"
    )
    customer = service.create_user(
        email="customer@example.test", name="Customer User", password="test-password"
    )

    response = client.put(
        f"/api/v1/users/{customer.public_id}",
        headers=auth_headers(admin),
        json={"name": "Updated Customer"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Updated Customer"
