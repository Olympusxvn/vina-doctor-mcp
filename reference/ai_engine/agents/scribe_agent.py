from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from ai_engine.agents.scribe_prompts import SCRIBE_SYSTEM_PROMPT, SCRIBE_USER_PROMPT
from ai_engine.domain.entities import ScribeResult, SessionInfo, TranscriptTurn
from ai_engine.infrastructure.clients.qwen_audio_client import QwenAudioClient

if TYPE_CHECKING:
    from ai_engine.infrastructure.clients.qwen_asr_client import QwenAsrClient

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

# Model names that should route through the dedicated ASR client instead of
# the multimodal conversation client.
_ASR_MODEL_PREFIXES = ("qwen3-asr", "qwen2-asr", "paraformer")


def _is_asr_model(model: str) -> bool:
    return any(model.lower().startswith(p) for p in _ASR_MODEL_PREFIXES)


class ScribeAgentError(Exception):
    """Raised when the Scribe Agent cannot produce a valid ScribeResult."""


class ScribeAgent:
    """Transcribes audio into a structured transcript with speaker diarization.

    Supports two backends:
    - ``QwenAudioClient`` (MultiModalConversation) for multimodal models that
      return structured JSON with speaker turns.
    - ``QwenAsrClient`` (QwenTranscription) for pure-ASR models like
      ``qwen3-asr-flash`` that return plain text transcripts.

    When the model is an ASR model, the plain transcript is wrapped into a
    single-speaker ``ScribeResult`` without diarization.

    Implements ``ScribeAgentProtocol``.
    """

    def __init__(
        self,
        client: QwenAudioClient,
        asr_client: QwenAsrClient | None = None,
    ) -> None:
        self._client = client
        self._asr_client = asr_client

    def transcribe(self, audio_path: Path, model: str | None = None) -> ScribeResult:
        effective_model = model or self._client._model  # noqa: SLF001

        # Route to dedicated ASR client for pure-ASR models.
        if _is_asr_model(effective_model):
            return self._transcribe_asr(audio_path, model=effective_model)

        # Multimodal path — structured JSON response.
        return self._transcribe_multimodal(audio_path, model=model)

    # ------------------------------------------------------------------
    # ASR path (Qwen3-ASR-Flash and compatible)
    # ------------------------------------------------------------------

    def _transcribe_asr(self, audio_path: Path, model: str) -> ScribeResult:
        """Use QwenAsrClient to transcribe then wrap result in ScribeResult."""
        if self._asr_client is None:
            raise ScribeAgentError(
                f"Model '{model}' requires an ASR client but none was injected. "
                "Ensure QwenAsrClient is wired in main.py."
            )

        asr_client = self._asr_client
        if model != asr_client._model:  # noqa: SLF001
            from ai_engine.infrastructure.clients.qwen_asr_client import QwenAsrClient

            asr_client = QwenAsrClient(model=model)

        transcript_text = asr_client.transcribe(audio_path)

        return ScribeResult(
            session_info=SessionInfo(
                detected_languages=[],
                audio_quality="unknown",
            ),
            transcript=[
                TranscriptTurn(
                    speaker="Speaker",
                    timestamp=None,
                    text=transcript_text,
                )
            ],
        )

    # ------------------------------------------------------------------
    # Multimodal path (Qwen3.5-Omni-Flash, etc.)
    # ------------------------------------------------------------------

    def _transcribe_multimodal(
        self, audio_path: Path, model: str | None
    ) -> ScribeResult:
        if model is not None:
            self._client._model = model  # noqa: SLF001

        messages = [
            {
                "role": "system",
                "content": [{"text": SCRIBE_SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [
                    {"audio": str(audio_path)},
                    {"text": SCRIBE_USER_PROMPT},
                ],
            },
        ]

        raw = self._client.call(messages)
        return self._parse(raw)

    def _parse(self, raw_response: str) -> ScribeResult:
        cleaned = _CODE_FENCE_RE.sub("", raw_response).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ScribeAgentError(
                f"Scribe model returned non-JSON response: {exc}\n\nRaw: {raw_response[:500]}"
            ) from exc

        info_raw = data.get("session_info", {})
        session_info = SessionInfo(
            detected_languages=info_raw.get("detected_languages", []),
            audio_quality=info_raw.get("audio_quality", "unknown"),
        )

        transcript = [
            TranscriptTurn(
                speaker=t.get("speaker", "Unknown"),
                timestamp=t.get("timestamp"),
                text=t.get("text", ""),
            )
            for t in data.get("transcript", [])
        ]

        return ScribeResult(session_info=session_info, transcript=transcript)
