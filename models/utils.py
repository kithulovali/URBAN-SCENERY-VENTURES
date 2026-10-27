from sqlalchemy import Text, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from settings import Model
from models.shared import Timestamp


class UserRole(Model, Timestamp):
    __tablename__ = "user_roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    users: Mapped[list["User"]] = relationship("User", back_populates="role")


class OrderStatus(Model, Timestamp):
    __tablename__ = "order_statuses"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="order_status_record")


class PaymentStatus(Model, Timestamp):
    __tablename__ = "payment_statuses"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="payment_status_record")


class PaymentMethod(Model, Timestamp):
    __tablename__ = "payment_methods"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="payment_method_record")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="payment_method_record")


class ProductStatus(Model, Timestamp):
    __tablename__ = "product_statuses"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    products: Mapped[list["Product"]] = relationship("Product", back_populates="product_status_record")


class _LookupValue:
    def __init__(self, value: str):
        self.value = value
    def __str__(self) -> str:
        return self.value


UserRole.Admin = _LookupValue("ADMIN")
UserRole.Customer = _LookupValue("CUSTOMER")
UserRole.Guest = _LookupValue("GUEST")
OrderStatus.Pending = _LookupValue("PENDING")
OrderStatus.Approved = _LookupValue("APPROVED")
OrderStatus.Cancelled = _LookupValue("CANCELLED")
OrderStatus.Shipped = _LookupValue("SHIPPED")
OrderStatus.Delivered = _LookupValue("DELIVERED")
PaymentStatus.Paid = _LookupValue("PAID")
PaymentStatus.Not_yet_paid = _LookupValue("NOT YET PAID")
PaymentStatus.Failed = _LookupValue("FAILED")
ProductStatus.Available = _LookupValue("AVAILABLE")
ProductStatus.Empty = _LookupValue("EMPTY")
