from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from ai_engine.domain.value_objects import PipelineStatus, SeverityFlag, UrgencyLevel


class TranscriptTurn(BaseModel):
    speaker: str
    timestamp: Optional[str] = None
    text: str


class MultilingualText(BaseModel):
    en: str = "Not discussed"
    vn: str = "Not discussed"
    fr: str = "Not discussed"
    ar: str = "Not discussed"


class SOAPNotes(BaseModel):
    subjective: MultilingualText = MultilingualText()
    objective: MultilingualText = MultilingualText()
    assessment: MultilingualText = MultilingualText()
    plan: MultilingualText = MultilingualText()


class MultilingualInstruction(BaseModel):
    en: str = "Not discussed"
    vn: str = "Not discussed"


class Medication(BaseModel):
    name: str
    dosage: str
    frequency: Optional[str] = None
    route: Optional[str] = None
    instructions: MultilingualInstruction = MultilingualInstruction()


class NextSteps(BaseModel):
    en: str = "Not discussed"
    vn: str = "Not discussed"


class Diagnostics(BaseModel):
    primary_diagnosis: str = "Not specified"
    icd10_code: str = ""
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ClinicalReport(BaseModel):
    chief_complaint: MultilingualText = MultilingualText()
    soap_notes: SOAPNotes = SOAPNotes()
    medications: list[Medication] = []
    icd10_codes: list[str] = []
    severity_flag: SeverityFlag = SeverityFlag.LOW
    urgency_level: UrgencyLevel = UrgencyLevel.LOW
    diagnostics: Optional[Diagnostics] = None
    next_steps: NextSteps = NextSteps()


class ConsultationMetadata(BaseModel):
    primary_language: str = "unknown"
    consultation_duration_estimate: Optional[str] = None
    session_id: Optional[str] = None
    model: Optional[str] = None


class SessionInfo(BaseModel):
    detected_languages: list[str] = []
    audio_quality: str = "unknown"


class ScribeResult(BaseModel):
    session_info: SessionInfo = SessionInfo()
    transcript: list[TranscriptTurn] = []


class ClinicalResult(BaseModel):
    clinical_report: ClinicalReport = ClinicalReport()
    multilingual_summary: MultilingualText = MultilingualText()


class MedicalReport(BaseModel):
    metadata: ConsultationMetadata = ConsultationMetadata()
    transcript: list[TranscriptTurn] = []
    clinical_report: ClinicalReport = ClinicalReport()
    multilingual_summary: MultilingualText = MultilingualText()


class PipelineState(BaseModel):
    status: PipelineStatus = PipelineStatus.PENDING
    current_step: str = ""
    error: Optional[str] = None
