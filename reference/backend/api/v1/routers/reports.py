from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.v1.deps import get_current_user_id, get_get_report_use_case
from backend.api.v1.schemas.report import (
    MedicationSchema,
    MultilingualTextSchema,
    ReportResponse,
    SOAPReportSchema,
    TranscriptTurnSchema,
)
from backend.application.use_cases.get_report_use_case import GetReportUseCase
from backend.domain.entities import Report
from backend.domain.errors import AccessDeniedError, NotFoundError

router = APIRouter(prefix="/consultations", tags=["reports"])


def _to_response(report: Report) -> ReportResponse:
    soap = report.soap
    return ReportResponse(
        id=report.id,
        consultation_id=report.consultation_id,
        soap=SOAPReportSchema(
            subjective=MultilingualTextSchema(**soap.subjective.model_dump()),
            objective=MultilingualTextSchema(**soap.objective.model_dump()),
            assessment=MultilingualTextSchema(**soap.assessment.model_dump()),
            plan=MultilingualTextSchema(**soap.plan.model_dump()),
            icd10_codes=soap.icd10_codes,
            medications=[MedicationSchema(**m.model_dump()) for m in soap.medications],
            severity=soap.severity,
        ),
        transcript=[TranscriptTurnSchema(**t.model_dump()) for t in report.transcript],
        created_at=report.created_at,
    )


@router.get(
    "/{consultation_id}/report",
    response_model=ReportResponse,
    summary="Get the SOAP report for a consultation",
)
async def get_report(
    consultation_id: UUID,
    doctor_id: UUID = Depends(get_current_user_id),
    use_case: GetReportUseCase = Depends(get_get_report_use_case),
) -> ReportResponse:
    try:
        report = await use_case.execute(
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
    return _to_response(report)
