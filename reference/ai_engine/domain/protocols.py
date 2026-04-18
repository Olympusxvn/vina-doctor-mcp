from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ai_engine.domain.entities import ClinicalResult, PipelineState, ScribeResult


class ScribeAgentProtocol(Protocol):
    """Transcribes audio into a structured transcript with speaker diarization."""

    def transcribe(
        self, audio_path: Path, model: str | None = None
    ) -> ScribeResult: ...


class ClinicalAgentProtocol(Protocol):
    """Analyses a cleaned transcript and produces a structured clinical report."""

    def analyze(
        self, transcript_text: str, model: str | None = None
    ) -> ClinicalResult: ...


class ModelSelectorProtocol(Protocol):
    """Selects the most appropriate LLM model for a given task type."""

    def select(self, task: str) -> str: ...


class PipelineStateTrackerProtocol(Protocol):
    """Tracks the state of a consultation processing pipeline."""

    def update(self, session_id: str, state: PipelineState) -> None: ...

    def get(self, session_id: str) -> PipelineState: ...


class TextCleanerProtocol(Protocol):
    """Redacts PII and normalises text before it reaches external LLMs."""

    def clean(self, text: str) -> str: ...


class ICD10SelectorProtocol(Protocol):
    """Selects relevant ICD-10 codes for a transcript and returns an enriched
    treatment reference block for the clinical agent.

    The ``enrich()`` method must be fail-safe: any internal error should be
    caught and an empty string returned so the pipeline continues unaffected.
    """

    def enrich(self, transcript: str) -> str:
        """Return an ICD-10 treatment reference block, or '' on failure."""
        ...
