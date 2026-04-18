from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MultilingualTextSchema(BaseModel):
    vn: str = ""
    en: str = ""
    fr: str = ""
    ar: str = ""


class MedicationSchema(BaseModel):
    name: str
    dosage: str
    frequency: str
    duration: str


class SOAPReportSchema(BaseModel):
    subjective: MultilingualTextSchema
    objective: MultilingualTextSchema
    assessment: MultilingualTextSchema
    plan: MultilingualTextSchema
    icd10_codes: list[str]
    medications: list[MedicationSchema]
    severity: str


class TranscriptTurnSchema(BaseModel):
    speaker: str
    timestamp: str | None = None
    text: str


class ReportResponse(BaseModel):
    id: UUID
    consultation_id: UUID
    soap: SOAPReportSchema
    transcript: list[TranscriptTurnSchema] = []
    created_at: datetime
