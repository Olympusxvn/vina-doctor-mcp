"""MCP tool: suggest_icd10 — clinical text → candidate ICD-10 codes."""

from __future__ import annotations

from typing import Any

from mcp_server.ai_engine_client import AIEngineClient, AIEngineError


async def suggest_icd10(
    clinical_text: str,
    max_suggestions: int = 5,
) -> dict[str, Any]:
    """Map a clinical description to candidate ICD-10 codes with confidence scores.

    Args:
        clinical_text: Free-text clinical description or transcript excerpt.
        max_suggestions: Maximum number of ICD-10 suggestions to return (1–10, default 5).

    Returns:
        A dict with ``suggestions`` (list of code/description/confidence/category)
        and ``primary`` (the top suggestion).
    """
    max_suggestions = max(1, min(10, max_suggestions))

    client = AIEngineClient()
    try:
        result = await client.post(
            "/v1/icd10/suggest",
            json={"clinical_text": clinical_text, "max_suggestions": max_suggestions},
        )
        return result
    except AIEngineError as exc:
        error: dict[str, Any] = {"error": str(exc)}
        if exc.status_code:
            error["status_code"] = exc.status_code
        if exc.status_code == 504:
            error["retry_after"] = 30
        return error
