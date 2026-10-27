from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict, AliasPath

class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=64, description="User full name")
    email: EmailStr = Field(..., description="User email address")
    contact: Optional[str] = Field(None, max_length=64, description="User phone number or contact info")

class UserRegister(UserBase):
    password: str = Field(..., min_length=6, max_length=128, description="User password")
    role: Optional[str] = Field(default="CUSTOMER", description="User role: ADMIN, CUSTOMER, GUEST")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=64)
    contact: Optional[str] = Field(None, max_length=64)

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    public_id: UUID
    name: str
    email: str
    role: str = Field(validation_alias=AliasPath("role", "name"))
    contact: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
