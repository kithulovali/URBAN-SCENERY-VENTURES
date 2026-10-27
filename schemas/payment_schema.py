from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    order_id: int = Field(..., description="ID of the order to pay for")
    payment_method: str = Field(..., description="Payment method: MOBILE MONEY, BANK, CRYPTO")
    amount: Decimal = Field(..., gt=0, description="Amount paid")


class PaymentProcessRequest(BaseModel):
    order_id: int = Field(..., description="Order ID to settle")
    payment_method: str = Field(..., description="Payment method: MOBILE MONEY, BANK, CRYPTO")
    account_reference: Optional[str] = Field(None, description="Phone number (Mobile Money), Wallet Address (Crypto), or Account Ref")


class PaymentOut(BaseModel):
    id: int
    payment_method: str
    amount: Decimal
    paid_at: datetime
    order_id: int

    model_config = ConfigDict(from_attributes=True)
