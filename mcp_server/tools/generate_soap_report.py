"""MCP tool: generate_soap_report — transcript → full SOAP with optional FHIR context."""

from __future__ import annotations

import logging
from typing import Any

from mcp_server.ai_engine_client import AIEngineClient, AIEngineError
from mcp_server.fhir_client import fetch_patient_context
from mcp_server.sharp import SharpContext

logger = logging.getLogger(__name__)


async def generate_soap_report(
    transcript: str,
    output_languages: list[str] | None = None,
    sharp_context: SharpContext | None = None,
) -> dict[str, Any]:
    """Generate a full multilingual SOAP report from a consultation transcript.

    When FHIR context is available (via SHARP headers), patient history is fetched
    from the FHIR server and injected into the clinical analysis for richer output.
    Works without FHIR context too — graceful degradation.

    Args:
        transcript: Raw consultation transcript text.
        output_languages: Languages for the report (default: ['en', 'vn', 'fr', 'ar']).
        sharp_context: SHARP/FHIR context extracted from HTTP headers (if any).

    Returns:
        Full ClinicalReport with SOAP notes, ICD-10, medications, severity, urgency,
        multilingual_summary, and fhir_context_used flag.
    """
    if output_languages is None:
        output_languages = ["en", "vn", "fr", "ar"]

    payload: dict[str, Any] = {
        "transcript": transcript,
        "output_languages": output_languages,
    }

    # Attempt FHIR enrichment when SHARP context is available
    fhir_used = False
    patient_context: str | None = None

    if sharp_context and sharp_context.is_complete and sharp_context.patient_id:
        try:
            patient_context = await fetch_patient_context(sharp_context)
        except Exception:  # noqa: BLE001
            logger.warning("FHIR enrichment failed — continuing without patient context")

        if patient_context:
            fhir_used = True
            payload["patient_context"] = patient_context
            payload["fhir_context"] = {
                "fhir_server_url": sharp_context.fhir_server_url,
                "patient_id": sharp_context.patient_id,
            }

    client = AIEngineClient()
    try:
        result = await client.post("/v1/consultations/analyze-transcript", json=payload)
        result["fhir_context_used"] = fhir_used
        return result
    except AIEngineError as exc:
        error: dict[str, Any] = {"error": str(exc), "fhir_context_used": fhir_used}
        if exc.status_code:
            error["status_code"] = exc.status_code
        if exc.status_code == 504:
            error["retry_after"] = 30
        return error
