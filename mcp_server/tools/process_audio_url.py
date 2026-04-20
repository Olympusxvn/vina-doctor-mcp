"""MCP tool: process_audio_url — download audio from URL → full SOAP pipeline."""

from __future__ import annotations

import logging
import mimetypes
from typing import Any
from urllib.parse import urlparse

import httpx

from mcp_server.ai_engine_client import AIEngineClient, AIEngineError

logger = logging.getLogger(__name__)

_DOWNLOAD_TIMEOUT = httpx.Timeout(timeout=60.0, connect=10.0)
_MAX_AUDIO_BYTES = 50 * 1024 * 1024  # 50 MB

_MIME_MAP = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".webm": "audio/webm",
    ".flac": "audio/flac",
}


def _guess_content_type(url: str) -> str:
    """Guess MIME type from URL path extension."""
    path = urlparse(url).path
    ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return _MIME_MAP.get(ext, mimetypes.guess_type(url)[0] or "audio/mpeg")


def _guess_filename(url: str) -> str:
    """Extract a reasonable filename from the URL."""
    path = urlparse(url).path
    name = path.rsplit("/", 1)[-1] if "/" in path else "audio.mp3"
    return name or "audio.mp3"


async def process_audio_url(
    audio_url: str,
    language_hint: str = "auto",
    pipeline_mode: str = "two_step",
) -> dict[str, Any]:
    """Download audio from a URL and generate a full SOAP medical report.

    Runs the complete pipeline: VAD → transcription (ScribeAgent) →
    PII redaction → clinical analysis (ClinicalAgent) → multilingual SOAP.

    Args:
        audio_url: Publicly accessible URL to audio file (mp3/wav/m4a/ogg/webm).
                   Max recommended duration: 10 minutes.
        language_hint: Primary spoken language — 'vi', 'en', 'fr', 'ar', or 'auto'.
        pipeline_mode: 'two_step' (Scribe→Clinical, default) or 'unified' (single-call).

    Returns:
        Full medical report: transcript with diarization, SOAP in 4 languages,
        ICD-10, medications, urgency level.
    """
    # Step 1: Download audio from URL
    try:
        async with httpx.AsyncClient(timeout=_DOWNLOAD_TIMEOUT) as http:
            resp = await http.get(audio_url)
            resp.raise_for_status()
            audio_bytes = resp.content
    except httpx.TimeoutException:
        return {"error": f"Timeout downloading audio from {audio_url}", "status_code": 504}
    except httpx.HTTPError as exc:
        return {"error": f"Failed to download audio: {exc}"}

    if len(audio_bytes) > _MAX_AUDIO_BYTES:
        return {"error": f"Audio file too large ({len(audio_bytes)} bytes, max {_MAX_AUDIO_BYTES})"}

    # Step 2: Upload to AI Engine as multipart
    content_type = _guess_content_type(audio_url)
    file_name = _guess_filename(audio_url)

    client = AIEngineClient()
    try:
        result = await client.post_multipart(
            "/v1/consultations/process-v2",
            file_name=file_name,
            file_bytes=audio_bytes,
            content_type=content_type,
            params={"mode": pipeline_mode},
        )
        return result
    except AIEngineError as exc:
        error: dict[str, Any] = {"error": str(exc)}
        if exc.status_code:
            error["status_code"] = exc.status_code
        if exc.status_code == 504:
            error["retry_after"] = 30
        return error
