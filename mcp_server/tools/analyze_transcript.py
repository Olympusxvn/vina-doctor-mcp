"""MCP tool: analyze_transcript — transcript text → structured SOAP + ICD-10."""

from __future__ import annotations

from typing import Any

from mcp_server.ai_engine_client import AIEngineClient, AIEngineError


async def analyze_transcript(
    transcript: str,
    language_hint: str = "auto",
) -> dict[str, Any]:
    """Analyse a medical consultation transcript and return a structured clinical report.

    Takes raw transcript text (may be multilingual, with dialog turns) and produces
    a full SOAP report with ICD-10 codes and multilingual summaries (EN/VN/FR/AR).

    Args:
        transcript: Raw consultation transcript text.
        language_hint: Language hint — 'vi', 'en', 'fr', 'ar', or 'auto' (default).

    Returns:
        A MedicalReport dict containing metadata, clinical_report (SOAP, ICD-10,
        medications, severity, urgency), and multilingual_summary.
    """
    client = AIEngineClient()
    try:
        result = await client.post(
            "/v1/consultations/analyze-transcript",
            json={"transcript": transcript, "language_hint": language_hint},
        )
        return result
    except AIEngineError as exc:
        error: dict[str, Any] = {"error": str(exc)}
        if exc.status_code:
            error["status_code"] = exc.status_code
        if exc.status_code == 504:
            error["retry_after"] = 30
        return error
