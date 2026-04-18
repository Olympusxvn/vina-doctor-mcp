from __future__ import annotations

from uuid import UUID

from backend.domain.entities import Consultation
from backend.domain.errors import AccessDeniedError
from backend.domain.repositories import ConsultationRepository


class GetConsultationUseCase:
    def __init__(self, consultation_repo: ConsultationRepository) -> None:
        self._consultation_repo = consultation_repo

    async def execute(self, consultation_id: UUID, doctor_id: UUID) -> Consultation:
        consultation = await self._consultation_repo.get_by_id(consultation_id)
        if consultation.doctor_id != doctor_id:
            raise AccessDeniedError()
        return consultation
