from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str | None
    role: str
    address_line1: str | None
    address_line2: str | None
    city: str | None
    province: str | None
    postal_code: str | None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = None
