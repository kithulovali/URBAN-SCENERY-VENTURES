from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.payment_model import Payment
from models.order_model import Order
from models.utils import PaymentStatus, OrderStatus, PaymentMethod
from services.lookup_service import get_lookup

_UPDATABLE_FIELDS = {"payment_method", "amount"}


def create_payment(order_id, payment_method="BANK", amount=None, session: Session | None = None) -> Payment:
    # Supports create_payment(order_id, method, amount, session) and create_payment(Payment(...), session).
    if isinstance(order_id, Payment):
        supplied_payment = order_id
        if isinstance(payment_method, Session):
            session = payment_method
        order_id = supplied_payment.order_id
        amount = supplied_payment.amount
        payment_method = getattr(supplied_payment, "_payment_method_name", "BANK")

    if session is None:
        raise TypeError("A database session is required")

    order_id = int(order_id)
    order = session.get(Order, order_id)
    if order is None:
        raise ValueError(f"Order with ID {order_id} not found")

    payment_amount = Decimal(str(amount if amount is not None else order.total_price))
    if payment_amount <= 0:
        raise ValueError("Payment amount must be greater than zero")
    if payment_amount != Decimal(str(order.total_price)):
        raise ValueError(f"Payment amount must equal the order total ({order.total_price})")

    existing = session.scalars(select(Payment).where(Payment.order_id == order_id)).first()
    if existing:
        raise ValueError(f"Payment already recorded for Order #{order_id}")

    # Resolve lookup rows before creating/attaching Payment to avoid relationship autoflush warnings.
    method = get_lookup(session, PaymentMethod, payment_method or "BANK")
    paid_status = get_lookup(session, PaymentStatus, "PAID")
    approved_status = get_lookup(session, OrderStatus, "APPROVED")

    payment = Payment(
        order=order,
        order_id=order_id,
        payment_method_record=method,
        amount=payment_amount,
    )
    session.add(payment)
    order.payment_status_record = paid_status
    order.order_status_record = approved_status
    session.commit()
    session.refresh(payment)
    return payment


def get_payment(payment_id: int, session: Session) -> Optional[Payment]:
    return session.get(Payment, payment_id)


def get_payment_by_order_id(order_id: int, session: Session) -> Optional[Payment]:
    return session.scalars(select(Payment).where(Payment.order_id == order_id)).first()


def get_all_payments(session: Session, offset: int = 0, limit: int = 100):
    return list(session.scalars(select(Payment).offset(offset).limit(limit)).all())


def update_payment(payment_id: int, updates: dict[str, object], session: Session) -> Optional[Payment]:
    payment = session.get(Payment, payment_id)
    if payment is None:
        return None
    for field, value in updates.items():
        if value is None or field not in _UPDATABLE_FIELDS:
            continue
        if field == "payment_method":
            payment.payment_method_record = get_lookup(session, PaymentMethod, str(value))
        elif field == "amount":
            new_amount = Decimal(str(value))
            if new_amount != Decimal(str(payment.order.total_price)):
                raise ValueError(f"Payment amount must equal the order total ({payment.order.total_price})")
            payment.amount = new_amount
    session.commit()
    session.refresh(payment)
    return payment


def delete_payment(payment_id: int, session: Session) -> bool:
    payment = session.get(Payment, payment_id)
    if payment is None:
        return False
    order = payment.order
    session.delete(payment)
    session.commit()
    # expire_on_commit=False sessions may retain the deleted child in the scalar relationship.
    if order is not None and order in session:
        session.expire(order, ["payment"])
    return True
