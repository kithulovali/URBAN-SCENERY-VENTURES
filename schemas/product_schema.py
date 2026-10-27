from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=128, description="Product / Electronics name")
    price: Decimal = Field(..., gt=0, description="Unit price")
    description: Optional[str] = Field(None, description="Detailed product description and specs")
    banner_image: Optional[str] = Field(None, description="Product image URL or path")
    quantity: int = Field(default=0, ge=0, description="Available inventory stock")
    status: Optional[str] = Field(default="AVAILABLE", description="Product availability status")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    price: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = None
    banner_image: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None


class ProductOut(BaseModel):
    id: int
    name: str
    price: Decimal
    description: Optional[str] = None
    banner_image: Optional[str] = None
    quantity: int
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
