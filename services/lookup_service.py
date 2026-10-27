from sqlalchemy import select
from sqlalchemy.orm import Session
from models.utils import UserRole, OrderStatus, PaymentStatus, PaymentMethod, ProductStatus

_LOOKUPS = {
    UserRole: ["ADMIN", "CUSTOMER", "GUEST"],
    OrderStatus: ["PENDING", "APPROVED", "CANCELLED", "SHIPPED", "DELIVERED"],
    PaymentStatus: ["PAID", "NOT YET PAID", "FAILED"],
    PaymentMethod: ["BANK", "MOBILE MONEY", "CRYPTO"],
    ProductStatus: ["AVAILABLE", "EMPTY"],
}

def seed_lookup_values(session: Session) -> None:
    for model, names in _LOOKUPS.items():
        existing = {row.name.upper() for row in session.scalars(select(model)).all()}
        for name in names:
            if name not in existing:
                session.add(model(name=name, description=name.replace("_", " ").title()))
    session.flush()

def get_lookup(session: Session, model, name: str):
    seed_lookup_values(session)
    normalized = str(getattr(name, "value", name) or "").strip().upper()
    if model is PaymentMethod:
        normalized = "MOBILE MONEY" if normalized in {"MOBILE_MONEY", "MOBILE-MONEY"} else normalized
    if model is PaymentStatus and normalized in {"NOT_YET_PAID", "NOT-YET-PAID"}:
        normalized = "NOT YET PAID"
    result = session.scalars(select(model).where(model.name == normalized)).first()
    if result is None:
        result = model(name=normalized, description=normalized.title())
        session.add(result)
        session.flush()
    return result
