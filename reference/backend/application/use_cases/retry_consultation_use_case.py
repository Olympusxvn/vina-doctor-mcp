from __future__ import annotations

import asyncio
from uuid import UUID

from backend.application.services.consultation_orchestrator import (
    ConsultationOrchestrator,
)
from backend.domain.entities import Consultation
from backend.domain.errors import AccessDeniedError
from backend.domain.repositories import ConsultationRepository
from backend.domain.value_objects import ConsultationStatus


class RetryConsultationUseCase:
    def __init__(
        self,
        consultation_repo: ConsultationRepository,
        orchestrator: ConsultationOrchestrator,
    ) -> None:
        self._consultation_repo = consultation_repo
        self._orchestrator = orchestrator

    async def execute(self, consultation_id: UUID, doctor_id: UUID) -> Consultation:
        consultation = await self._consultation_repo.get_by_id(consultation_id)

        if consultation.doctor_id != doctor_id:
            raise AccessDeniedError()

        if consultation.status != ConsultationStatus.FAILED:
            raise ValueError(
                f"Cannot retry consultation with status '{consultation.status.value}'. "
                "Only FAILED consultations can be retried."
            )

        await self._consultation_repo.update_status(
            consultation_id, ConsultationStatus.PENDING
        )

        asyncio.create_task(self._orchestrator.run(consultation_id))

        return await self._consultation_repo.get_by_id(consultation_id)
