from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from schemas.product_schema import ProductOut


class OrderCreate(BaseModel):
    product_id: int = Field(..., gt=0, description="ID of the electronics product to buy")
    quantity: int = Field(default=1, ge=1, le=100, description="Number of items to purchase")
    address: str = Field(..., min_length=5, max_length=255, description="Delivery / Shipping address")
    contact: str = Field(..., min_length=5, max_length=64, description="Contact phone number")
    payment_method: Optional[str] = Field(default="BANK", description="Preferred payment method")


class OrderStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_status: str = Field(..., min_length=3, max_length=32, description="Administrative fulfilment status; payment status is provider-controlled")


class OrderOut(BaseModel):
    id: int
    address: str
    contacs: str
    order_status: str
    payment_method: str
    payment_status: str
    initial_price: Decimal
    total_price: Decimal
    quantity: int
    ordered_at: datetime
    user_id: Optional[UUID] = None
    product_id: int
    product: Optional[ProductOut] = None

    model_config = ConfigDict(from_attributes=True)
