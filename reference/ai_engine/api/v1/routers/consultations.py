from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status, Query

from ai_engine.api.v1.schemas.consultation_schemas import (
    ErrorResponse,
    ProcessAudioResponse,
    ProcessConsultationResponse,
)
from ai_engine.application.use_cases.process_audio_use_case import (
    ProcessAudioError,
    ProcessAudioUseCase,
)
from ai_engine.application.use_cases.process_consultation_use_case import (
    ProcessConsultationError,
    ProcessConsultationUseCase,
)
from ai_engine.domain.value_objects import PipelineMode

router = APIRouter(prefix="/v1/consultations", tags=["consultations"])


def _get_use_case() -> ProcessAudioUseCase:
    """Dependency injector — resolved by the app factory in main.py."""
    from ai_engine.main import get_process_audio_use_case  # noqa: PLC0415

    return get_process_audio_use_case()


def _get_consultation_use_case() -> ProcessConsultationUseCase:
    """Dependency injector — resolved by the app factory in main.py."""
    from ai_engine.main import get_process_consultation_use_case  # noqa: PLC0415

    return get_process_consultation_use_case()


@router.post(
    "/process",
    response_model=ProcessAudioResponse,
    responses={
        422: {"model": ErrorResponse, "description": "VAD rejection or bad format"},
        500: {"model": ErrorResponse, "description": "Pipeline or API error"},
    },
    summary="Process a medical consultation audio file",
    description=(
        "Accepts an audio upload, runs VAD, calls Qwen2-Audio with the master "
        "medical scribe prompt, and returns a structured multilingual SOAP report."
    ),
)
async def process_consultation(
    file: UploadFile,
    model: str = Query(
        default="qwen3.5-omni-flash",
        description="Qwen model to use. Use 'qwen3.5-omni-flash' for all audio tasks.",
    ),
    use_case: ProcessAudioUseCase = Depends(_get_use_case),
) -> ProcessAudioResponse:
    """Upload an audio file and receive a structured medical report."""

    audio_bytes = await file.read()

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        audio_path = work_dir / (file.filename or "audio.mp3")
        audio_path.write_bytes(audio_bytes)

        try:
            report = use_case.execute(
                audio_path,
                work_dir=work_dir,
                model=model,
            )
        except ProcessAudioError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    return ProcessAudioResponse(
        metadata=report.metadata,
        transcript=report.transcript,
        clinical_report=report.clinical_report,
        multilingual_summary=report.multilingual_summary,
    )


@router.post(
    "/process-v2",
    response_model=ProcessConsultationResponse,
    responses={
        422: {"model": ErrorResponse, "description": "VAD rejection or bad format"},
        500: {"model": ErrorResponse, "description": "Pipeline or API error"},
    },
    summary="Process a medical consultation audio (multi-agent pipeline)",
    description=(
        "Accepts an audio upload and runs either a unified (single-call) or "
        "two-step (Scribe → Clinical) pipeline, returning a structured "
        "multilingual SOAP report with diagnostics and urgency assessment."
    ),
)
async def process_consultation_v2(
    file: UploadFile,
    mode: PipelineMode = Query(
        default=PipelineMode.TWO_STEP,
        description="Pipeline mode: 'unified' (single LLM call) or 'two_step' (Scribe → Clinical).",
    ),
    model: str = Query(
        default="",
        description="Optional model override. Leave empty for automatic selection.",
    ),
    use_case: ProcessConsultationUseCase = Depends(_get_consultation_use_case),
) -> ProcessConsultationResponse:
    """Upload an audio file and receive a structured medical report via the multi-agent pipeline."""

    audio_bytes = await file.read()

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        audio_path = work_dir / (file.filename or "audio.mp3")
        audio_path.write_bytes(audio_bytes)

        try:
            report = use_case.execute(
                audio_path,
                work_dir=work_dir,
                mode=mode,
                model=model or None,
            )
        except ProcessConsultationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    return ProcessConsultationResponse(
        metadata=report.metadata,
        transcript=report.transcript,
        clinical_report=report.clinical_report,
        multilingual_summary=report.multilingual_summary,
    )
