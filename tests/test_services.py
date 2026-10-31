from decimal import Decimal

import pytest

from models import Order, Payment, Product, User
from models.utils import ProductStatus
from services.lookup_service import get_lookup
from services.order_service import create_order, delete_order
from services.payment_service import create_payment, delete_payment, update_payment
from services.user_service import UserService


def make_product(session, quantity=5):
    product = Product(
        name="Test product",
        price=Decimal("25.00"),
        quantity=quantity,
        product_status_record=get_lookup(session, ProductStatus, "AVAILABLE"),
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


def test_user_service_create_and_remove_by_private_id(session):
    service = UserService(session)
    user = service.create_user(
        email="customer@example.test", name="Test Customer", password="test-password"
    )
    private_id = user.private_id

    assert user.role.name == "CUSTOMER"
    assert service.get_by_email("CUSTOMER@example.test").private_id == private_id
    assert service.remove_user(private_id=private_id) is True
    assert service.get_user(private_id) is None


def test_order_restores_stock_when_deleted_before_payment(session):
    product = make_product(session)
    order = create_order(
        product_id=product.id, quantity=2, address="123 Test Road",
        contact="0700000000", session=session
    )
    assert session.get(Product, product.id).quantity == 3

    assert delete_order(order.id, session) is True
    assert session.get(Product, product.id).quantity == 5
    assert session.get(Order, order.id) is None


def test_payment_crud_and_order_deletion_do_not_emit_orm_warnings(session):
    product = make_product(session)
    order = create_order(
        product_id=product.id, quantity=1, address="123 Test Road",
        contact="0700000000", session=session
    )
    payment = create_payment(
        order.id, payment_method="BANK", amount=order.total_price, session=session
    )
    assert payment.order_id == order.id
    assert session.get(Order, order.id).payment_status == "PAID"

    updated = update_payment(payment.id, {"amount": str(order.total_price)}, session)
    assert updated.amount == Decimal(str(order.total_price))
    try:
        update_payment(payment.id, {"amount": "30.00"}, session)
    except ValueError as error:
        assert "must equal the order total" in str(error)
    else:
        raise AssertionError("A payment amount different from the order total must be rejected")
    payment_id = payment.id
    order_id = order.id

    assert delete_payment(payment_id, session) is True
    assert session.get(Payment, payment_id) is None
    with pytest.raises(ValueError, match="cannot be deleted"):
        delete_order(order_id, session)
    assert session.get(Order, order_id) is not None

def test_order_creation_reserves_stock_and_rolls_back_failed_reservation(session):
    product = make_product(session, quantity=5)

    first_order = create_order(
        product_id=product.id, quantity=4, address="123 Test Road",
        contact="0700000000", session=session
    )
    assert session.get(Product, product.id).quantity == 1

    try:
        create_order(
            product_id=product.id, quantity=2, address="123 Test Road",
            contact="0700000000", session=session
        )
    except ValueError as error:
        assert "Insufficient stock" in str(error)
    else:
        raise AssertionError("An order exceeding remaining stock must be rejected")

    assert session.get(Product, product.id).quantity == 1
    assert len(session.query(Order).filter_by(product_id=product.id).all()) == 1
    assert session.get(Order, first_order.id) is not None


def test_order_creation_rejects_zero_quantity_without_changing_stock(session):
    product = make_product(session, quantity=5)

    try:
        create_order(
            product_id=product.id, quantity=0, address="123 Test Road",
            contact="0700000000", session=session
        )
    except ValueError as error:
        assert "at least 1" in str(error)
    else:
        raise AssertionError("Zero-quantity orders must be rejected")

    assert session.get(Product, product.id).quantity == 5
    assert session.query(Order).filter_by(product_id=product.id).count() == 0

