"""MCP tool: summarize_for_patient — clinical report → patient-friendly summary."""

from __future__ import annotations

import json
from typing import Any

from mcp_server.ai_engine_client import AIEngineClient, AIEngineError


async def summarize_for_patient(
    clinical_report_json: str,
    target_language: str = "vn",
    reading_level: str = "simple",
) -> dict[str, Any]:
    """Convert a clinical SOAP report into a patient-friendly plain-language summary.

    Designed for patients who may not understand medical terminology.
    The output avoids jargon and focuses on what the patient needs to do.

    Args:
        clinical_report_json: JSON string of the clinical_report object returned
                               by analyze_transcript or generate_soap_report.
        target_language: Primary language for the summary — 'vn', 'en', 'fr', 'ar'.
        reading_level: 'simple' (default, plain language) or 'standard'.

    Returns:
        summary, summary_en, key_actions, medications_plain, follow_up, urgency_note.
    """
    # Parse the clinical report JSON — accept both string and dict
    if isinstance(clinical_report_json, str):
        try:
            clinical_report = json.loads(clinical_report_json)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON in clinical_report_json"}
    else:
        clinical_report = clinical_report_json

    client = AIEngineClient()
    try:
        result = await client.post(
            "/v1/consultations/patient-summary",
            json={
                "clinical_report": clinical_report,
                "target_language": target_language,
                "reading_level": reading_level,
            },
        )
        return result
    except AIEngineError as exc:
        error: dict[str, Any] = {"error": str(exc)}
        if exc.status_code:
            error["status_code"] = exc.status_code
        if exc.status_code == 504:
            error["retry_after"] = 30
        return error
