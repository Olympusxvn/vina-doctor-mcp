from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from backend.domain.value_objects import ConsultationStatus


class ConsultationResponse(BaseModel):
    id: UUID
    doctor_id: UUID
    status: ConsultationStatus
    created_at: datetime
    updated_at: datetime


class ConsultationListResponse(BaseModel):
    items: list[ConsultationResponse]
    total: int
