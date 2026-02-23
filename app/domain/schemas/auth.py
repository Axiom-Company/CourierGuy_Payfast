from __future__ import annotations
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserBriefResponse


class UserBriefResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str | None
    role: str

    class Config:
        from_attributes = True
