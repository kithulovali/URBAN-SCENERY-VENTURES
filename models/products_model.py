from sqlalchemy import DECIMAL, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from settings import Model
from models.shared import Timestamp
from models.utils import ProductStatus


class Product(Model, Timestamp):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    price: Mapped[float] = mapped_column(DECIMAL, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    banner_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    product_status_id: Mapped[int] = mapped_column(ForeignKey("product_statuses.id"), nullable=False)
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="product")
    product_status_record: Mapped["ProductStatus"] = relationship("ProductStatus", back_populates="products")

    @property
    def status(self) -> str:
        return self.product_status_record.name if self.product_status_record else getattr(self, "_status_name", "AVAILABLE")
    @status.setter
    def status(self, value: str) -> None:
        self._status_name = str(getattr(value, "value", value)).strip().upper()
