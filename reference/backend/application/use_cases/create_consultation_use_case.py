from __future__ import annotations

import asyncio
from uuid import UUID

from backend.domain.entities import Consultation
from backend.domain.repositories import ConsultationRepository
from backend.application.services.consultation_orchestrator import (
    ConsultationOrchestrator,
)
from backend.domain.value_objects import ConsultationStatus
from backend.infrastructure.storage.audio_storage_protocol import AudioStorageProtocol


class CreateConsultationUseCase:
    """
    Persists a new consultation, stores audio, and triggers AI processing
    asynchronously in the background (fire-and-return: 202 pattern).
    """

    def __init__(
        self,
        consultation_repo: ConsultationRepository,
        audio_storage: AudioStorageProtocol,
        orchestrator: ConsultationOrchestrator,
    ) -> None:
        self._consultation_repo = consultation_repo
        self._audio_storage = audio_storage
        self._orchestrator = orchestrator

    async def execute(
        self,
        doctor_id: UUID,
        audio_bytes: bytes,
        filename: str,
        model: str | None = None,
    ) -> Consultation:
        consultation = Consultation(
            doctor_id=doctor_id,
            audio_path="",  # updated after storage
            status=ConsultationStatus.PENDING,
        )

        audio_path = await self._audio_storage.save(
            consultation.id, audio_bytes, filename
        )

        # Pydantic frozen model — rebuild with audio_path set
        consultation = consultation.model_copy(update={"audio_path": audio_path})
        saved = await self._consultation_repo.save(consultation)

        # Fire-and-forget: AI processing runs in background
        asyncio.create_task(self._orchestrator.run(saved.id, model=model))

        return saved
