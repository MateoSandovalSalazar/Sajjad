import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.passwords import validate_password


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: EmailStr
    full_name: str
    company: str
    is_verified: bool
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = None
    company: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    # Misma política que en el registro y el restablecimiento: si no,
    # este endpoint sería la puerta trasera para poner "a" de
    # contraseña.
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password(v)
