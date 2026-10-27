from datetime import datetime
from sqlalchemy import DECIMAL, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from settings import Model


class Payment(Model):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    amount: Mapped[float] = mapped_column(DECIMAL, nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    payment_method_id: Mapped[int] = mapped_column(ForeignKey("payment_methods.id"), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="payment")
    payment_method_record: Mapped["PaymentMethod"] = relationship("PaymentMethod", back_populates="payments")

    @property
    def payment_method(self) -> str:
        return self.payment_method_record.name if self.payment_method_record else getattr(self, "_payment_method_name", "BANK")

    @payment_method.setter
    def payment_method(self, value: str) -> None:
        self._payment_method_name = str(getattr(value, "value", value)).strip().upper()
