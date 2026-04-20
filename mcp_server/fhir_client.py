"""FHIR client — fetch patient context from a FHIR R4 server.

Used by generate_soap_report when SHARP headers provide a FHIR server URL,
access token, and patient ID. The fetched context (demographics, conditions,
medications) is formatted as a plain-text summary for injection into the
clinical analysis prompt.

Fail-safe: any FHIR error is logged and returns an empty context — the tool
continues without enrichment rather than failing.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from mcp_server.sharp import SharpContext

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(timeout=15.0, connect=5.0)


class FHIRClient:
    """Async client for fetching patient context from a FHIR R4 server."""

    def __init__(self, ctx: SharpContext) -> None:
        if not ctx.fhir_server_url:
            raise ValueError("fhir_server_url is required")
        self._base_url = ctx.fhir_server_url.rstrip("/")
        self._headers: dict[str, str] = {"Accept": "application/fhir+json"}
        if ctx.fhir_access_token:
            token = ctx.fhir_access_token
            if not token.startswith("Bearer "):
                token = f"Bearer {token}"
            self._headers["Authorization"] = token

    async def _get(self, path: str) -> dict[str, Any] | None:
        """GET a FHIR resource. Returns None on any error."""
        url = f"{self._base_url}/{path}"
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, headers=self._headers) as client:
                resp = await client.get(url)
                if resp.status_code == 404:
                    logger.debug("FHIR resource not found: %s", path)
                    return None
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("FHIR fetch failed for %s: %s", path, exc)
            return None

    async def get_patient(self, patient_id: str) -> dict[str, Any] | None:
        """Fetch Patient/{id} resource."""
        return await self._get(f"Patient/{patient_id}")

    async def get_conditions(self, patient_id: str) -> list[dict[str, Any]]:
        """Fetch active Condition resources for a patient."""
        bundle = await self._get(f"Condition?patient={patient_id}&clinical-status=active")
        if not bundle or bundle.get("resourceType") != "Bundle":
            return []
        return [entry["resource"] for entry in bundle.get("entry", []) if "resource" in entry]

    async def get_medications(self, patient_id: str) -> list[dict[str, Any]]:
        """Fetch active MedicationStatement resources for a patient."""
        bundle = await self._get(f"MedicationStatement?patient={patient_id}&status=active")
        if not bundle or bundle.get("resourceType") != "Bundle":
            return []
        return [entry["resource"] for entry in bundle.get("entry", []) if "resource" in entry]


def _extract_patient_demographics(patient: dict[str, Any]) -> str:
    """Extract basic demographics from a FHIR Patient resource."""
    parts: list[str] = []

    # Name
    names = patient.get("name", [])
    if names:
        name = names[0]
        given = " ".join(name.get("given", []))
        family = name.get("family", "")
        full_name = f"{given} {family}".strip()
        if full_name:
            parts.append(f"Name: {full_name}")

    # Gender + birth date
    if gender := patient.get("gender"):
        parts.append(f"Gender: {gender}")
    if birth_date := patient.get("birthDate"):
        parts.append(f"Date of birth: {birth_date}")

    return ", ".join(parts) if parts else "Demographics unavailable"


def _extract_condition_summary(conditions: list[dict[str, Any]]) -> str:
    """Summarize active conditions into a readable list."""
    if not conditions:
        return "No active conditions on record"

    items: list[str] = []
    for c in conditions[:10]:  # cap at 10
        code_info = c.get("code", {})
        codings = code_info.get("coding", [])
        if codings:
            display = codings[0].get("display", "Unknown condition")
            code = codings[0].get("code", "")
            items.append(f"- {display} ({code})" if code else f"- {display}")
        elif text := code_info.get("text"):
            items.append(f"- {text}")

    return "\n".join(items) if items else "No active conditions on record"


def _extract_medication_summary(medications: list[dict[str, Any]]) -> str:
    """Summarize active medications into a readable list."""
    if not medications:
        return "No active medications on record"

    items: list[str] = []
    for m in medications[:10]:  # cap at 10
        med = m.get("medicationCodeableConcept", {})
        codings = med.get("coding", [])
        if codings:
            display = codings[0].get("display", "Unknown medication")
            items.append(f"- {display}")
        elif text := med.get("text"):
            items.append(f"- {text}")
        elif ref := m.get("medicationReference", {}).get("display"):
            items.append(f"- {ref}")

    return "\n".join(items) if items else "No active medications on record"


async def fetch_patient_context(ctx: SharpContext) -> str | None:
    """Fetch patient context from FHIR and return a formatted summary string.

    Returns None if FHIR context is incomplete or any fetch fails entirely.
    Partial data is still returned (e.g. patient found but no conditions).
    """
    if not ctx.is_complete or not ctx.patient_id:
        return None

    try:
        fhir = FHIRClient(ctx)
    except ValueError:
        return None

    patient = await fhir.get_patient(ctx.patient_id)
    if patient is None:
        logger.info("Patient %s not found in FHIR — skipping enrichment", ctx.patient_id)
        return None

    conditions = await fhir.get_conditions(ctx.patient_id)
    medications = await fhir.get_medications(ctx.patient_id)

    demographics = _extract_patient_demographics(patient)
    condition_summary = _extract_condition_summary(conditions)
    medication_summary = _extract_medication_summary(medications)

    return (
        "--- Patient Context (from FHIR) ---\n"
        f"Patient: {demographics}\n"
        f"\nActive Conditions:\n{condition_summary}\n"
        f"\nCurrent Medications:\n{medication_summary}\n"
        "--- End Patient Context ---"
    )
