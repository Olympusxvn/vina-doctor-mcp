from __future__ import annotations

from pathlib import Path

from ai_engine.agents.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from ai_engine.infrastructure.clients.qwen_audio_client import QwenAudioClient


class MedicalExtractor:
    """Assembles the DashScope message payload and calls the Qwen audio model.

    Returns the raw response string (expected to be a JSON blob).
    Callers (reporter.py) are responsible for parsing and validating it.
    """

    def __init__(self, client: QwenAudioClient) -> None:
        self._client = client

    def extract(self, audio_path: Path, model: str | None = None) -> str:
        """Send *audio_path* to the Qwen model and return the raw JSON string.

        Args:
            audio_path: Local path to the (pre-processed) audio file.
            model:      Optional model override (e.g. "qwen-audio-max").

        Returns:
            Raw string response from the model.
        """
        if model is not None:
            self._client._model = model  # noqa: SLF001 – intentional override

        messages = [
            {
                "role": "system",
                "content": [{"text": SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [
                    {"audio": str(audio_path)},
                    {"text": USER_PROMPT_TEMPLATE},
                ],
            },
        ]

        return self._client.call(messages)
