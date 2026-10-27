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
        supplied = order_id
        if isinstance(payment_method, Session):
            session = payment_method
        order_id = supplied.order_id
        amount = supplied.amount
        payment_method = getattr(supplied, "_payment_method_name", "BANK")
    if session is None:
        raise TypeError("A database session is required")
    order = session.get(Order, int(order_id))
    if order is None:
        raise ValueError(f"Order with ID {order_id} not found")
    existing = session.scalars(select(Payment).where(Payment.order_id == int(order_id))).first()
    if existing:
        raise ValueError(f"Payment already recorded for Order #{order_id}")
    method = get_lookup(session, PaymentMethod, payment_method or "BANK")
    payment = Payment(order=order, order_id=int(order_id), payment_method_record=method,
                      amount=Decimal(str(amount if amount is not None else order.total_price)))
    order.payment_status_record = get_lookup(session, PaymentStatus, "PAID")
    order.order_status_record = get_lookup(session, OrderStatus, "APPROVED")
    session.add(payment)
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
            payment.amount = Decimal(str(value))
    session.commit()
    session.refresh(payment)
    return payment

def delete_payment(payment_id: int, session: Session) -> bool:
    payment = session.get(Payment, payment_id)
    if payment is None:
        return False
    session.delete(payment)
    session.commit()
    return True
