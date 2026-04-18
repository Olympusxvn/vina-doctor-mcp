from abc import ABC, abstractmethod
from pathlib import Path


class AudioRepositoryProtocol(ABC):
    """Defines the contract for temporary audio storage during a consultation session."""

    @abstractmethod
    def save(self, audio_bytes: bytes, filename: str) -> Path:
        """Persist raw audio bytes and return the local path."""

    @abstractmethod
    def delete(self, path: Path) -> None:
        """Remove the audio file once processing is complete."""
