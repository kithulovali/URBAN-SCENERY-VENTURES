from datetime import datetime
import uuid
from sqlalchemy import DateTime, DECIMAL, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from settings import Model
from models.utils import OrderStatus, PaymentStatus, PaymentMethod


class Order(Model):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    contacs: Mapped[str] = mapped_column(String(64), nullable=False)
    initial_price: Mapped[float] = mapped_column(DECIMAL, nullable=False)
    total_price: Mapped[float] = mapped_column(DECIMAL, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    order_status_id: Mapped[int] = mapped_column(ForeignKey("order_statuses.id"), nullable=False)
    payment_method_id: Mapped[int] = mapped_column(ForeignKey("payment_methods.id"), nullable=False)
    payment_status_id: Mapped[int] = mapped_column(ForeignKey("payment_statuses.id"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.private_id"), nullable=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user: Mapped["User | None"] = relationship("User", back_populates="orders")
    product: Mapped["Product"] = relationship("Product", back_populates="orders")
    payment: Mapped["Payment | None"] = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    order_status_record: Mapped["OrderStatus"] = relationship("OrderStatus", back_populates="orders")
    payment_status_record: Mapped["PaymentStatus"] = relationship("PaymentStatus", back_populates="orders")
    payment_method_record: Mapped["PaymentMethod"] = relationship("PaymentMethod", back_populates="orders")

    @property
    def order_status(self) -> str:
        return self.order_status_record.name if self.order_status_record else getattr(self, "_order_status_name", "PENDING")
    @order_status.setter
    def order_status(self, value: str) -> None:
        self._order_status_name = str(getattr(value, "value", value)).strip().upper()

    @property
    def payment_status(self) -> str:
        return self.payment_status_record.name if self.payment_status_record else getattr(self, "_payment_status_name", "NOT YET PAID")
    @payment_status.setter
    def payment_status(self, value: str) -> None:
        self._payment_status_name = str(getattr(value, "value", value)).strip().upper()

    @property
    def payment_method(self) -> str:
        return self.payment_method_record.name if self.payment_method_record else getattr(self, "_payment_method_name", "BANK")
    @payment_method.setter
    def payment_method(self, value: str) -> None:
        self._payment_method_name = str(getattr(value, "value", value)).strip().upper()
