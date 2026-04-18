from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from backend.domain.value_objects import ConsultationStatus


class TranscriptTurn(BaseModel):
    """A single speaker turn in the consultation transcript."""

    speaker: str
    timestamp: str | None = None
    text: str

    model_config = {"frozen": True}


class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    email: str
    hashed_password: str
    full_name: str
    specialty: str = ""
    license_number: str = ""
    phone: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": True}


class Consultation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    doctor_id: UUID
    audio_path: str
    status: ConsultationStatus = ConsultationStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": True}


class MultilingualText(BaseModel):
    vn: str = ""
    en: str = ""
    fr: str = ""
    ar: str = ""

    model_config = {"frozen": True}


class Medication(BaseModel):
    name: str
    dosage: str
    frequency: str
    duration: str

    model_config = {"frozen": True}


class SOAPReport(BaseModel):
    """SOAP report produced by AI engine — multilingual, with ICD-10 codes."""

    subjective: MultilingualText
    objective: MultilingualText
    assessment: MultilingualText
    plan: MultilingualText
    icd10_codes: list[str] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    severity: str = ""

    model_config = {"frozen": True}


class Report(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    consultation_id: UUID
    soap: SOAPReport
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": True}
