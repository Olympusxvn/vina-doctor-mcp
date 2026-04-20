"""FastMCP server — tool registration and transport entry point."""

from __future__ import annotations

import functools

from mcp.server.fastmcp import FastMCP

from mcp_server.config import MCP_HOST, MCP_PORT

mcp = FastMCP(
    "vina-doctor",
    instructions=(
        "Medical AI toolkit powered by vina-doctor. "
        "Provides tools for clinical transcript analysis, SOAP report generation, "
        "ICD-10 code suggestion, patient-friendly summaries, and audio processing. "
        "Supports multilingual output (EN, VN, FR, AR)."
    ),
    host=MCP_HOST,
    port=MCP_PORT,
)

# ---------------------------------------------------------------------------
# Declare FHIR context extension for Prompt Opinion platform.
# When Prompt Opinion sees this in the initialize response, it shows a
# "Trust this server with FHIR context" toggle to the user.
# ---------------------------------------------------------------------------
_FHIR_EXTENSION: dict[str, dict] = {
    "ai.promptopinion/fhir-context": {},
}

# Patch create_initialization_options to always include our extension.
_original_create_init = mcp._mcp_server.create_initialization_options  # noqa: SLF001


@functools.wraps(_original_create_init)
def _create_init_with_fhir(notification_options=None, experimental_capabilities=None):
    merged = dict(_FHIR_EXTENSION)
    if experimental_capabilities:
        merged.update(experimental_capabilities)
    return _original_create_init(
        notification_options=notification_options,
        experimental_capabilities=merged,
    )


mcp._mcp_server.create_initialization_options = _create_init_with_fhir  # noqa: SLF001


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@mcp.tool()
async def ping() -> str:
    """Health-check tool. Returns 'pong' to verify MCP connectivity."""
    return "pong"


@mcp.tool()
async def analyze_transcript(
    transcript: str,
    language_hint: str = "auto",
) -> dict:
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
    from mcp_server.tools.analyze_transcript import (  # noqa: PLC0415
        analyze_transcript as _impl,
    )

    return await _impl(transcript, language_hint)


@mcp.tool()
async def suggest_icd10(
    clinical_text: str,
    max_suggestions: int = 5,
) -> dict:
    """Map a clinical description to candidate ICD-10 codes with confidence scores.

    Args:
        clinical_text: Free-text clinical description or transcript excerpt.
        max_suggestions: Maximum number of ICD-10 suggestions to return (1–10, default 5).

    Returns:
        A dict with ``suggestions`` (list of code/description/confidence/category)
        and ``primary`` (the top suggestion).
    """
    from mcp_server.tools.suggest_icd10 import (  # noqa: PLC0415
        suggest_icd10 as _impl,
    )

    return await _impl(clinical_text, max_suggestions)


@mcp.tool()
async def generate_soap_report(
    transcript: str,
    output_languages: list[str] | None = None,
    ctx: None = None,
) -> dict:
    """Generate a full multilingual SOAP report from a consultation transcript.

    When FHIR context is available (via SHARP headers from Prompt Opinion),
    patient history is fetched and injected for richer output. Works without
    FHIR context too — graceful degradation.

    Args:
        transcript: Raw consultation transcript text.
        output_languages: Languages for the report (default: ['en', 'vn', 'fr', 'ar']).

    Returns:
        Full ClinicalReport with SOAP notes, ICD-10, medications, severity, urgency,
        multilingual_summary, and fhir_context_used flag.
    """
    from mcp_server.sharp import SharpContext  # noqa: PLC0415
    from mcp_server.tools.generate_soap_report import (  # noqa: PLC0415
        generate_soap_report as _impl,
    )

    # Try to extract SHARP context from the MCP request
    sharp = SharpContext()
    try:
        from mcp_server.sharp import get_sharp_context  # noqa: PLC0415

        if ctx is not None:
            sharp = get_sharp_context(ctx)
    except Exception:  # noqa: BLE001
        pass

    return await _impl(transcript, output_languages, sharp)


@mcp.tool()
async def summarize_for_patient(
    clinical_report_json: str,
    target_language: str = "vn",
    reading_level: str = "simple",
) -> dict:
    """Convert a clinical SOAP report into a patient-friendly plain-language summary.

    Designed for patients who may not understand medical terminology.
    The output avoids jargon and focuses on what the patient needs to do.

    Args:
        clinical_report_json: JSON string of the clinical_report object returned
                               by analyze_transcript or generate_soap_report.
        target_language: Primary language for the summary — 'vn' (default), 'en', 'fr', 'ar'.
        reading_level: 'simple' (default, plain language) or 'standard'.

    Returns:
        summary, summary_en, key_actions, medications_plain, follow_up, urgency_note.
    """
    from mcp_server.tools.summarize_for_patient import (  # noqa: PLC0415
        summarize_for_patient as _impl,
    )

    return await _impl(clinical_report_json, target_language, reading_level)


@mcp.tool()
async def process_audio_url(
    audio_url: str,
    language_hint: str = "auto",
    pipeline_mode: str = "two_step",
) -> dict:
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
    from mcp_server.tools.process_audio_url import (  # noqa: PLC0415
        process_audio_url as _impl,
    )

    return await _impl(audio_url, language_hint, pipeline_mode)


@mcp.tool()
async def get_consultation_status(
    session_id: str,
) -> dict:
    """Poll the status of an async consultation processing job.

    Use this after process_audio_url to check whether the pipeline has
    finished and retrieve the result.

    Args:
        session_id: Session ID returned by process_audio_url.

    Returns:
        session_id, status (PENDING/PROCESSING/COMPLETED/FAILED),
        current_step, result (when completed), error (if failed).
    """
    from mcp_server.tools.get_consultation_status import (  # noqa: PLC0415
        get_consultation_status as _impl,
    )

    return await _impl(session_id)
