from __future__ import annotations

from uuid import UUID

from backend.domain.entities import Report
from backend.domain.errors import AccessDeniedError
from backend.domain.repositories import ConsultationRepository, ReportRepository


class GetReportUseCase:
    def __init__(
        self,
        consultation_repo: ConsultationRepository,
        report_repo: ReportRepository,
    ) -> None:
        self._consultation_repo = consultation_repo
        self._report_repo = report_repo

    async def execute(self, consultation_id: UUID, doctor_id: UUID) -> Report:
        consultation = await self._consultation_repo.get_by_id(consultation_id)
        if consultation.doctor_id != doctor_id:
            raise AccessDeniedError()
        return await self._report_repo.get_by_consultation(consultation_id)
