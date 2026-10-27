from decimal import Decimal
from typing import Optional
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from models.products_model import Product
from models.utils import ProductStatus
from services.lookup_service import get_lookup

_UPDATABLE_FIELDS = {"name", "price", "description", "banner_image", "quantity", "status"}

def create_product(product: Product, session: Session) -> Product:
    status_name = getattr(product, "_status_name", "AVAILABLE")
    product.product_status_record = get_lookup(session, ProductStatus, status_name)
    session.add(product)
    session.commit()
    session.refresh(product)
    return product

def get_product(product_id: int, session: Session) -> Optional[Product]:
    return session.get(Product, product_id)

def get_all_products(session: Session, offset: int = 0, limit: int = 100,
                     search: Optional[str] = None, min_price: Optional[Decimal] = None,
                     max_price: Optional[Decimal] = None, status: Optional[str] = None):
    statement = select(Product)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(or_(Product.name.ilike(pattern), Product.description.ilike(pattern)))
    if min_price is not None:
        statement = statement.where(Product.price >= min_price)
    if max_price is not None:
        statement = statement.where(Product.price <= max_price)
    if status:
        statement = statement.join(Product.product_status_record).where(ProductStatus.name == str(status).strip().upper())
    return list(session.scalars(statement.offset(offset).limit(limit)).all())

def update_product(product_id: int, updates: dict[str, object], session: Session) -> Optional[Product]:
    product = session.get(Product, product_id)
    if product is None:
        return None
    for field, value in updates.items():
        if field not in _UPDATABLE_FIELDS or value is None:
            continue
        if field == "status":
            product.product_status_record = get_lookup(session, ProductStatus, str(value))
        else:
            setattr(product, field, value)
    if product.quantity <= 0:
        product.product_status_record = get_lookup(session, ProductStatus, "EMPTY")
    elif product.status == "EMPTY":
        product.product_status_record = get_lookup(session, ProductStatus, "AVAILABLE")
    session.commit()
    session.refresh(product)
    return product

def reduce_product_stock(product_id: int, quantity_to_reduce: int, session: Session) -> Optional[Product]:
    product = session.get(Product, product_id)
    if product is None or quantity_to_reduce < 1 or product.quantity < quantity_to_reduce:
        return None
    product.quantity -= quantity_to_reduce
    if product.quantity == 0:
        product.product_status_record = get_lookup(session, ProductStatus, "EMPTY")
    session.commit()
    session.refresh(product)
    return product

def delete_product(product_id: int, session: Session) -> bool:
    product = session.get(Product, product_id)
    if product is None:
        return False
    session.delete(product)
    session.commit()
    return True
