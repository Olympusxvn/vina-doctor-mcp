from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserProfileResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    specialty: str = ""
    license_number: str = ""
    phone: str = ""
    created_at: datetime


class UserProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    specialty: str | None = None
    license_number: str | None = None
    phone: str | None = None
