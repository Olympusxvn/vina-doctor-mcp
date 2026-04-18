from __future__ import annotations

from typing import Optional
from pydantic import BaseModel

from ai_engine.domain.entities import (
    ClinicalReport,
    ConsultationMetadata,
    MultilingualText,
    PipelineState,
    TranscriptTurn,
)


class ProcessAudioResponse(BaseModel):
    """HTTP response schema for POST /v1/consultations/process."""

    metadata: ConsultationMetadata
    transcript: list[TranscriptTurn]
    clinical_report: ClinicalReport
    multilingual_summary: MultilingualText


class ProcessConsultationResponse(BaseModel):
    """HTTP response schema for POST /v1/consultations/process-v2."""

    metadata: ConsultationMetadata
    transcript: list[TranscriptTurn]
    clinical_report: ClinicalReport
    multilingual_summary: MultilingualText


class PipelineStateResponse(BaseModel):
    """HTTP response schema for GET /v1/consultations/{session_id}/status."""

    session_id: str
    state: PipelineState


class ErrorResponse(BaseModel):
    """Uniform error body returned on 4xx / 5xx responses."""

    detail: str
    code: Optional[str] = None
