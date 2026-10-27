from decimal import Decimal

from fastapi.testclient import TestClient
import pytest

from core.security import create_access_token
from main import app
from models import Payment, Product
from models.utils import ProductStatus
from services.lookup_service import get_lookup
from services.order_service import create_order
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


def test_payment_endpoint_does_not_fake_success_without_provider(client, session):
    service = UserService(session)
    customer = service.create_user(
        email="payment.customer@example.test", name="Payment Customer", password="test-password"
    )
    product = Product(
        name="Payment test product",
        price=Decimal("25.00"),
        quantity=2,
        product_status_record=get_lookup(session, ProductStatus, "AVAILABLE"),
    )
    session.add(product)
    session.commit()
    order = create_order(
        product_id=product.id, quantity=1, address="123 Payment Road",
        contact="0700000000", session=session, user_id=customer.private_id
    )

    response = client.post(
        "/api/v1/payments/pay",
        headers=auth_headers(customer),
        json={"order_id": order.id, "payment_method": "BANK", "amount": "25.00"},
    )

    assert response.status_code == 501
    assert "no payment was recorded" in response.json()["detail"].lower()
    assert session.get(Payment, 1) is None
    assert session.get(type(order), order.id).payment_status == "NOT YET PAID"


def test_order_details_require_authentication_and_owner_access(client, session):
    service = UserService(session)
    owner = service.create_user(
        email="order.owner@example.test", name="Order Owner", password="test-password"
    )
    other = service.create_user(
        email="order.other@example.test", name="Other Customer", password="test-password"
    )
    product = Product(
        name="Order privacy product", price=Decimal("10.00"), quantity=3,
        product_status_record=get_lookup(session, ProductStatus, "AVAILABLE"),
    )
    session.add(product)
    session.commit()
    order = create_order(
        product_id=product.id, quantity=1, address="123 Privacy Road",
        contact="0700000000", session=session, user_id=owner.private_id
    )

    anonymous = client.get(f"/api/v1/orders/{order.id}")
    assert anonymous.status_code == 401

    forbidden = client.get(
        f"/api/v1/orders/{order.id}", headers=auth_headers(other)
    )
    assert forbidden.status_code == 403

    own_order = client.get(
        f"/api/v1/orders/{order.id}", headers=auth_headers(owner)
    )
    assert own_order.status_code == 200
    assert own_order.json()["id"] == order.id



def test_business_intelligence_agent_requires_admin(client, session):
    service = UserService(session)
    customer = service.create_user(
        email="ai.customer@example.test", name="AI Customer", password="test-password"
    )
    anonymous = client.post(
        "/api/v1/ai/agents/business-intelligence", json={"question": "Summarize sales"}
    )
    assert anonymous.status_code == 401

    forbidden = client.post(
        "/api/v1/ai/agents/business-intelligence",
        headers=auth_headers(customer),
        json={"question": "Summarize sales"},
    )
    assert forbidden.status_code == 403


def test_admin_can_use_business_intelligence_agent(client, session):
    admin = UserService(session).create_user(
        email="ai.admin@example.test", name="AI Admin", password="test-password", role="ADMIN"
    )
    response = client.post(
        "/api/v1/ai/agents/business-intelligence",
        headers=auth_headers(admin),
        json={"question": "Summarize sales"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["agent"] == "business_intelligence"


def test_marketing_content_agent_requires_admin(client, session):
    customer = UserService(session).create_user(
        email="marketing.customer@example.test",
        name="Marketing Customer",
        password="test-password",
    )
    anonymous = client.post(
        "/api/v1/ai/agents/marketing-content", json={"question": "Write a caption"}
    )
    assert anonymous.status_code == 401

    forbidden = client.post(
        "/api/v1/ai/agents/marketing-content",
        headers=auth_headers(customer),
        json={"question": "Write a caption"},
    )
    assert forbidden.status_code == 403


def test_product_discovery_rate_limit_returns_429(client, session, monkeypatch):
    import routers.agents as agents_router

    agents_router._discovery_requests.clear()
    monkeypatch.setattr(
        agents_router,
        "run_agent",
        lambda agent, question, db: {
            "agent": agent,
            "answer": "test",
            "model": "deterministic-fallback",
            "data_summary": {},
        },
    )
    try:
        for _ in range(agents_router._DISCOVERY_LIMIT):
            response = client.post(
                "/api/v1/ai/agents/product-discovery",
                json={"question": "Find a desk"},
            )
            assert response.status_code == 200, response.text

        limited = client.post(
            "/api/v1/ai/agents/product-discovery",
            json={"question": "Find a desk"},
        )
        assert limited.status_code == 429
        assert limited.headers["retry-after"] == "60"
    finally:
        agents_router._discovery_requests.clear()
