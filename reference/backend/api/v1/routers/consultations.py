from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import Response

from backend.api.v1.deps import (
    get_create_consultation_use_case,
    get_current_user_id,
    get_get_consultation_audio_use_case,
    get_get_consultation_use_case,
    get_list_consultations_use_case,
    get_retry_consultation_use_case,
)
from backend.api.v1.schemas.consultation import (
    ConsultationListResponse,
    ConsultationResponse,
)
from backend.application.use_cases.create_consultation_use_case import (
    CreateConsultationUseCase,
)
from backend.application.use_cases.get_consultation_audio_use_case import (
    GetConsultationAudioUseCase,
)
from backend.application.use_cases.get_consultation_use_case import (
    GetConsultationUseCase,
)
from backend.application.use_cases.list_consultations_use_case import (
    ListConsultationsUseCase,
)
from backend.application.use_cases.retry_consultation_use_case import (
    RetryConsultationUseCase,
)
from backend.domain.entities import Consultation
from backend.domain.errors import AccessDeniedError, NotFoundError

router = APIRouter(prefix="/consultations", tags=["consultations"])


def _to_response(c: Consultation) -> ConsultationResponse:
    return ConsultationResponse(
        id=c.id,
        doctor_id=c.doctor_id,
        status=c.status,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.post(
    "",
    response_model=ConsultationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload audio and start consultation processing",
)
async def create_consultation(
    file: UploadFile,
    model: str | None = Query(default=None),
    doctor_id: UUID = Depends(get_current_user_id),
    use_case: CreateConsultationUseCase = Depends(get_create_consultation_use_case),
) -> ConsultationResponse:
    audio_bytes = await file.read()
    consultation = await use_case.execute(
        doctor_id=doctor_id,
        audio_bytes=audio_bytes,
        filename=file.filename or "audio.mp3",
        model=model,
    )
    return _to_response(consultation)


@router.get(
    "",
    response_model=ConsultationListResponse,
    summary="List consultations for the current doctor",
)
async def list_consultations(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    doctor_id: UUID = Depends(get_current_user_id),
    use_case: ListConsultationsUseCase = Depends(get_list_consultations_use_case),
) -> ConsultationListResponse:
    items = await use_case.execute(doctor_id=doctor_id, offset=offset, limit=limit)
    return ConsultationListResponse(
        items=[_to_response(c) for c in items],
        total=len(items),
    )


@router.post(
    "/{consultation_id}/retry",
    response_model=ConsultationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry a failed consultation",
)
async def retry_consultation(
    consultation_id: UUID,
    doctor_id: UUID = Depends(get_current_user_id),
    use_case: RetryConsultationUseCase = Depends(get_retry_consultation_use_case),
) -> ConsultationResponse:
    try:
        consultation = await use_case.execute(
            consultation_id=consultation_id, doctor_id=doctor_id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except AccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return _to_response(consultation)


@router.get(
    "/{consultation_id}/audio",
    summary="Stream the uploaded audio for a consultation",
    response_class=Response,
)
async def get_consultation_audio(
    consultation_id: UUID,
    doctor_id: UUID = Depends(get_current_user_id),
    use_case: GetConsultationAudioUseCase = Depends(
        get_get_consultation_audio_use_case
    ),
) -> Response:
    try:
        audio_bytes, media_type, filename = await use_case.execute(
            consultation_id=consultation_id, doctor_id=doctor_id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except AccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    return Response(
        content=audio_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Accept-Ranges": "bytes",
        },
    )


@router.get(
    "/{consultation_id}",
    response_model=ConsultationResponse,
    summary="Get a single consultation",
)
async def get_consultation(
    consultation_id: UUID,
    doctor_id: UUID = Depends(get_current_user_id),
    use_case: GetConsultationUseCase = Depends(get_get_consultation_use_case),
) -> ConsultationResponse:
    try:
        consultation = await use_case.execute(
            consultation_id=consultation_id, doctor_id=doctor_id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except AccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    return _to_response(consultation)
