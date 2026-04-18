from __future__ import annotations

from uuid import UUID

from backend.domain.repositories import ConsultationRepository
from backend.domain.value_objects import ConsultationStatus
from backend.infrastructure.clients.ai_engine_protocol import AiEngineClientProtocol
from backend.infrastructure.storage.audio_storage_protocol import AudioStorageProtocol
from backend.domain.entities import Report as DomainReport
from backend.domain.repositories import ReportRepository


class ConsultationOrchestrator:
    """
    Delegates audio processing to the AI engine and persists the resulting report.
    Single responsibility: bridge between ai_engine and persistence.
    """

    def __init__(
        self,
        ai_engine: AiEngineClientProtocol,
        audio_storage: AudioStorageProtocol,
        consultation_repo: ConsultationRepository,
        report_repo: ReportRepository,
    ) -> None:
        self._ai_engine = ai_engine
        self._audio_storage = audio_storage
        self._consultation_repo = consultation_repo
        self._report_repo = report_repo

    async def run(
        self, consultation_id: UUID, model: str | None = None
    ) -> DomainReport:
        consultation = await self._consultation_repo.get_by_id(consultation_id)

        await self._consultation_repo.update_status(
            consultation_id, ConsultationStatus.PROCESSING
        )

        try:
            audio_bytes = await self._audio_storage.read(consultation.audio_path)
            filename = consultation.audio_path.split("/")[-1]

            soap, transcript = await self._ai_engine.process_consultation(
                audio_bytes=audio_bytes,
                filename=filename,
                model=model,
            )

            report = DomainReport(
                consultation_id=consultation_id,
                soap=soap,
                transcript=transcript,
            )
            saved_report = await self._report_repo.save(report)

            await self._consultation_repo.update_status(
                consultation_id, ConsultationStatus.DONE
            )
            return saved_report

        except Exception:
            await self._consultation_repo.update_status(
                consultation_id, ConsultationStatus.FAILED
            )
            raise
