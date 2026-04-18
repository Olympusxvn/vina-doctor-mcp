from __future__ import annotations

from uuid import UUID

from backend.domain.entities import Consultation
from backend.domain.repositories import ConsultationRepository


class ListConsultationsUseCase:
    def __init__(self, consultation_repo: ConsultationRepository) -> None:
        self._consultation_repo = consultation_repo

    async def execute(
        self,
        doctor_id: UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Consultation]:
        return await self._consultation_repo.list_by_doctor(
            doctor_id, offset=offset, limit=limit
        )
