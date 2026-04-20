"""MCP tool: get_consultation_status — poll async job status."""

from __future__ import annotations

from typing import Any

from mcp_server.ai_engine_client import AIEngineClient, AIEngineError


async def get_consultation_status(
    session_id: str,
) -> dict[str, Any]:
    """Poll the status of an async consultation processing job.

    Use this after process_audio_url to check whether the pipeline has
    finished and retrieve the result.

    Args:
        session_id: Session ID returned by process_audio_url.

    Returns:
        session_id, status (PENDING/PROCESSING/COMPLETED/FAILED),
        current_step, result (MedicalReport when completed), error (if failed).
    """
    client = AIEngineClient()
    try:
        return await client.get(f"/v1/consultations/{session_id}/status")
    except AIEngineError as exc:
        error: dict[str, Any] = {"error": str(exc)}
        if exc.status_code:
            error["status_code"] = exc.status_code
        return error
