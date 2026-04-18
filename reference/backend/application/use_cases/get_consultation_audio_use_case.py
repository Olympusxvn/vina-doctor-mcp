from __future__ import annotations

from pathlib import Path
from uuid import UUID

from backend.domain.errors import AccessDeniedError, NotFoundError
from backend.domain.repositories import ConsultationRepository
from backend.infrastructure.storage.audio_storage_protocol import AudioStorageProtocol


class GetConsultationAudioUseCase:
    """
    Return the raw audio bytes and detected media type for a consultation.
    Enforces ownership: only the owning doctor may download the audio.
    """

    _MIME_MAP: dict[str, str] = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
        ".flac": "audio/flac",
    }

    def __init__(
        self,
        consultation_repo: ConsultationRepository,
        audio_storage: AudioStorageProtocol,
    ) -> None:
        self._consultation_repo = consultation_repo
        self._audio_storage = audio_storage

    async def execute(
        self, consultation_id: UUID, doctor_id: UUID
    ) -> tuple[bytes, str, str]:
        """
        Returns (audio_bytes, media_type, filename).
        Raises NotFoundError or AccessDeniedError.
        """
        try:
            consultation = await self._consultation_repo.get_by_id(consultation_id)
        except Exception as exc:
            raise NotFoundError(f"Consultation {consultation_id} not found") from exc

        if consultation.doctor_id != doctor_id:
            raise AccessDeniedError("Access denied")

        if not consultation.audio_path:
            raise NotFoundError("Audio file not available for this consultation")

        audio_bytes = await self._audio_storage.read(consultation.audio_path)

        suffix = Path(consultation.audio_path).suffix.lower()
        media_type = self._MIME_MAP.get(suffix, "application/octet-stream")
        filename = Path(consultation.audio_path).name

        return audio_bytes, media_type, filename
