from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models.order_model import Order
from models.products_model import Product
from models.utils import OrderStatus, PaymentStatus, PaymentMethod, ProductStatus
from services.lookup_service import get_lookup


def create_order(product_id, quantity=None, address=None, contact=None, payment_method="BANK",
                 session: Session | None = None, user_id: Optional[UUID] = None) -> Order:
    if isinstance(product_id, Order):
        supplied_order = product_id
        if isinstance(quantity, Session):
            session = quantity
        if session is None:
            raise TypeError("A database session is required")
        product_id, quantity = supplied_order.product_id, supplied_order.quantity
        address = supplied_order.address
        contact = getattr(supplied_order, "contacs", None) or getattr(supplied_order, "contact", None)
        payment_method = getattr(supplied_order, "_payment_method_name", "BANK")
        user_id = supplied_order.user_id
    if session is None:
        raise TypeError("A database session is required")

    quantity = 1 if quantity is None else int(quantity)
    if quantity < 1:
        raise ValueError("Order quantity must be at least 1")

    try:
        result = session.execute(
            update(Product)
            .where(Product.id == int(product_id), Product.quantity >= quantity)
            .values(quantity=Product.quantity - quantity)
            .execution_options(synchronize_session="fetch")
        )
        if result.rowcount != 1:
            product = session.get(Product, int(product_id))
            if product is None:
                raise ValueError(f"Product with id {product_id} not found")
            raise ValueError(
                f"Insufficient stock for product '{product.name}'. "
                f"Available: {product.quantity}, Requested: {quantity}"
            )

        product = session.get(Product, int(product_id))
        if product is None:
            raise ValueError(f"Product with id {product_id} not found")
        if product.quantity == 0:
            product.product_status_record = get_lookup(session, ProductStatus, "EMPTY")

        unit_price = Decimal(str(product.price))
        order = Order(
            address=(address or "").strip(),
            contacs=(contact or "").strip(),
            order_status_record=get_lookup(session, OrderStatus, "PENDING"),
            payment_method_record=get_lookup(session, PaymentMethod, payment_method or "BANK"),
            payment_status_record=get_lookup(session, PaymentStatus, "NOT YET PAID"),
            initial_price=unit_price,
            total_price=unit_price * quantity,
            quantity=quantity,
            product=product,
            user_id=user_id,
        )
        session.add(order)
        session.commit()
        session.refresh(order)
        return order
    except Exception:
        session.rollback()
        raise


def get_order(order_id: int, session: Session) -> Optional[Order]:
    return session.get(Order, order_id)


def get_all_orders(session: Session, offset: int = 0, limit: int = 100):
    return list(session.scalars(select(Order).offset(offset).limit(limit)).all())


def get_user_orders(user_id: UUID, session: Session):
    return list(session.scalars(select(Order).where(Order.user_id == user_id)).all())


def update_order(order_id: int, updates: dict[str, object], session: Session) -> Optional[Order]:
    order = session.get(Order, order_id)
    if order is None:
        return None

    try:
        requested_status = updates.get("order_status")
        if requested_status is not None:
            new_status = str(requested_status).strip().upper()
            old_status = order.order_status
            if new_status == "CANCELLED" and old_status != "CANCELLED":
                product = order.product
                if product is not None:
                    product.quantity += order.quantity
                    if product.status == "EMPTY" or product.quantity > 0:
                        product.product_status_record = get_lookup(session, ProductStatus, "AVAILABLE")
            elif old_status == "CANCELLED" and new_status != "CANCELLED":
                product = order.product
                if product is None:
                    raise ValueError("The product for this order no longer exists")
                result = session.execute(
                    update(Product)
                    .where(Product.id == product.id, Product.quantity >= order.quantity)
                    .values(quantity=Product.quantity - order.quantity)
                    .execution_options(synchronize_session="fetch")
                )
                if result.rowcount != 1:
                    raise ValueError("Insufficient stock to reactivate this cancelled order")
                product = session.get(Product, product.id)
                if product.quantity == 0:
                    product.product_status_record = get_lookup(session, ProductStatus, "EMPTY")
            order.order_status_record = get_lookup(session, OrderStatus, new_status)

        # Payment status is deliberately not accepted here. Only a verified payment
        # provider callback may mark an order paid.
        session.commit()
        session.refresh(order)
        return order
    except Exception:
        session.rollback()
        raise


def delete_order(order_id: int, session: Session) -> bool:
    order = session.get(Order, order_id)
    if order is None:
        return False
    if order.payment_status == "PAID" or order.order_status in {"SHIPPED", "DELIVERED"}:
        raise ValueError("Paid or fulfilled orders cannot be deleted; use the audited cancellation/refund workflow")
    try:
        if order.product and order.order_status != "CANCELLED":
            order.product.quantity += order.quantity
            if order.product.quantity > 0:
                order.product.product_status_record = get_lookup(session, ProductStatus, "AVAILABLE")
        session.delete(order)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
