from decimal import Decimal
from typing import Optional
from uuid import UUID
from sqlalchemy import select
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
    quantity = int(quantity or 1)
    product = session.get(Product, int(product_id))
    if product is None:
        raise ValueError(f"Product with id {product_id} not found")
    if quantity < 1 or product.quantity < quantity:
        raise ValueError(f"Insufficient stock for product '{product.name}'. Available: {product.quantity}, Requested: {quantity}")
    product.quantity -= quantity
    if product.quantity == 0:
        product.product_status_record = get_lookup(session, ProductStatus, "EMPTY")
    unit_price = Decimal(str(product.price))
    order = Order(address=(address or "").strip(), contacs=(contact or "").strip(),
        order_status_record=get_lookup(session, OrderStatus, "PENDING"),
        payment_method_record=get_lookup(session, PaymentMethod, payment_method or "BANK"),
        payment_status_record=get_lookup(session, PaymentStatus, "NOT YET PAID"),
        initial_price=unit_price, total_price=unit_price * quantity, quantity=quantity,
        product=product, user_id=user_id)
    session.add(order)
    session.commit()
    session.refresh(order)
    return order

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
    lookup_fields = {
        "order_status": (OrderStatus, "order_status_record"),
        "payment_status": (PaymentStatus, "payment_status_record"),
        "payment_method": (PaymentMethod, "payment_method_record"),
    }
    for field, value in updates.items():
        if value is None:
            continue
        if field in lookup_fields:
            model, relationship_name = lookup_fields[field]
            setattr(order, relationship_name, get_lookup(session, model, str(value)))
        elif field in {"address", "contacs", "quantity"}:
            setattr(order, field, value)
    session.commit()
    session.refresh(order)
    return order

def delete_order(order_id: int, session: Session) -> bool:
    order = session.get(Order, order_id)
    if order is None:
        return False
    if order.product and order.order_status in {"PENDING", "CANCELLED"}:
        order.product.quantity += order.quantity
        if order.product.status == "EMPTY":
            order.product.product_status_record = get_lookup(session, ProductStatus, "AVAILABLE")
    session.delete(order)
    session.commit()
    return True
