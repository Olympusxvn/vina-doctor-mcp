"""Tests for FHIR client — patient context fetching and formatting."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server.fhir_client import (
    FHIRClient,
    _extract_condition_summary,
    _extract_medication_summary,
    _extract_patient_demographics,
    fetch_patient_context,
)
from mcp_server.sharp import SharpContext

# ---------------------------------------------------------------------------
# Sample FHIR resources
# ---------------------------------------------------------------------------

FHIR_PATIENT = {
    "resourceType": "Patient",
    "id": "p-42",
    "name": [{"given": ["Nguyen", "Van"], "family": "An"}],
    "gender": "male",
    "birthDate": "1985-03-15",
}

FHIR_CONDITIONS_BUNDLE = {
    "resourceType": "Bundle",
    "type": "searchset",
    "entry": [
        {
            "resource": {
                "resourceType": "Condition",
                "code": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/sid/icd-10",
                            "code": "E11.9",
                            "display": "Type 2 diabetes mellitus without complications",
                        }
                    ]
                },
            }
        },
        {
            "resource": {
                "resourceType": "Condition",
                "code": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/sid/icd-10",
                            "code": "I10",
                            "display": "Essential hypertension",
                        }
                    ]
                },
            }
        },
    ],
}

FHIR_MEDICATIONS_BUNDLE = {
    "resourceType": "Bundle",
    "type": "searchset",
    "entry": [
        {
            "resource": {
                "resourceType": "MedicationStatement",
                "medicationCodeableConcept": {"coding": [{"display": "Metformin 500mg"}]},
            }
        },
        {
            "resource": {
                "resourceType": "MedicationStatement",
                "medicationCodeableConcept": {"coding": [{"display": "Lisinopril 10mg"}]},
            }
        },
    ],
}

EMPTY_BUNDLE = {"resourceType": "Bundle", "type": "searchset", "entry": []}


# ---------------------------------------------------------------------------
# Extract helpers
# ---------------------------------------------------------------------------


class TestExtractPatientDemographics:
    def test_full_patient(self):
        result = _extract_patient_demographics(FHIR_PATIENT)
        assert "Nguyen Van An" in result
        assert "male" in result
        assert "1985-03-15" in result

    def test_empty_patient(self):
        result = _extract_patient_demographics({})
        assert result == "Demographics unavailable"

    def test_partial_name(self):
        patient = {"name": [{"family": "Tran"}], "gender": "female"}
        result = _extract_patient_demographics(patient)
        assert "Tran" in result
        assert "female" in result


class TestExtractConditionSummary:
    def test_with_conditions(self):
        conditions = FHIR_CONDITIONS_BUNDLE["entry"]
        resources = [e["resource"] for e in conditions]
        result = _extract_condition_summary(resources)
        assert "Type 2 diabetes" in result
        assert "E11.9" in result
        assert "Essential hypertension" in result

    def test_empty_conditions(self):
        result = _extract_condition_summary([])
        assert "No active conditions" in result

    def test_text_fallback(self):
        conditions = [{"code": {"text": "Chronic back pain"}}]
        result = _extract_condition_summary(conditions)
        assert "Chronic back pain" in result


class TestExtractMedicationSummary:
    def test_with_medications(self):
        meds = FHIR_MEDICATIONS_BUNDLE["entry"]
        resources = [e["resource"] for e in meds]
        result = _extract_medication_summary(resources)
        assert "Metformin 500mg" in result
        assert "Lisinopril 10mg" in result

    def test_empty_medications(self):
        result = _extract_medication_summary([])
        assert "No active medications" in result

    def test_medication_reference_fallback(self):
        meds = [{"medicationReference": {"display": "Aspirin 81mg"}}]
        result = _extract_medication_summary(meds)
        assert "Aspirin 81mg" in result


# ---------------------------------------------------------------------------
# FHIRClient
# ---------------------------------------------------------------------------


class TestFHIRClient:
    def test_init_requires_url(self):
        ctx = SharpContext(fhir_server_url=None, fhir_access_token="token")
        with pytest.raises(ValueError, match="fhir_server_url"):
            FHIRClient(ctx)

    def test_init_adds_bearer_prefix(self):
        ctx = SharpContext(
            fhir_server_url="https://fhir.example.com/r4",
            fhir_access_token="raw-token",
        )
        client = FHIRClient(ctx)
        assert client._headers["Authorization"] == "Bearer raw-token"

    def test_init_preserves_bearer(self):
        ctx = SharpContext(
            fhir_server_url="https://fhir.example.com/r4",
            fhir_access_token="Bearer already-prefixed",
        )
        client = FHIRClient(ctx)
        assert client._headers["Authorization"] == "Bearer already-prefixed"

    @pytest.mark.asyncio
    async def test_get_patient_success(self):
        ctx = SharpContext(
            fhir_server_url="https://fhir.example.com/r4",
            fhir_access_token="Bearer token",
        )
        client = FHIRClient(ctx)

        with patch("mcp_server.fhir_client.httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = FHIR_PATIENT
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(return_value=mock_resp)
            mock_http.return_value = mock_ctx

            result = await client.get_patient("p-42")

        assert result is not None
        assert result["id"] == "p-42"

    @pytest.mark.asyncio
    async def test_get_patient_404(self):
        ctx = SharpContext(
            fhir_server_url="https://fhir.example.com/r4",
            fhir_access_token="Bearer token",
        )
        client = FHIRClient(ctx)

        with patch("mcp_server.fhir_client.httpx.AsyncClient") as mock_http:
            mock_resp = AsyncMock()
            mock_resp.status_code = 404
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(return_value=mock_resp)
            mock_http.return_value = mock_ctx

            result = await client.get_patient("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_patient_network_error(self):
        ctx = SharpContext(
            fhir_server_url="https://fhir.example.com/r4",
            fhir_access_token="Bearer token",
        )
        client = FHIRClient(ctx)

        with patch("mcp_server.fhir_client.httpx.AsyncClient") as mock_http:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
            mock_http.return_value = mock_ctx

            result = await client.get_patient("p-42")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_conditions_success(self):
        ctx = SharpContext(
            fhir_server_url="https://fhir.example.com/r4",
            fhir_access_token="Bearer token",
        )
        client = FHIRClient(ctx)

        with patch("mcp_server.fhir_client.httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = FHIR_CONDITIONS_BUNDLE
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(return_value=mock_resp)
            mock_http.return_value = mock_ctx

            result = await client.get_conditions("p-42")

        assert len(result) == 2
        assert result[0]["resourceType"] == "Condition"


# ---------------------------------------------------------------------------
# fetch_patient_context (integration)
# ---------------------------------------------------------------------------


class TestFetchPatientContext:
    @pytest.mark.asyncio
    async def test_full_context(self):
        ctx = SharpContext(
            fhir_server_url="https://fhir.example.com/r4",
            fhir_access_token="Bearer token",
            patient_id="p-42",
        )

        with patch("mcp_server.fhir_client.FHIRClient") as mock_fhir_cls:
            mock_fhir = mock_fhir_cls.return_value
            mock_fhir.get_patient = AsyncMock(return_value=FHIR_PATIENT)
            mock_fhir.get_conditions = AsyncMock(
                return_value=[e["resource"] for e in FHIR_CONDITIONS_BUNDLE["entry"]]
            )
            mock_fhir.get_medications = AsyncMock(
                return_value=[e["resource"] for e in FHIR_MEDICATIONS_BUNDLE["entry"]]
            )

            result = await fetch_patient_context(ctx)

        assert result is not None
        assert "Nguyen Van An" in result
        assert "Type 2 diabetes" in result
        assert "Metformin" in result
        assert "--- Patient Context (from FHIR) ---" in result

    @pytest.mark.asyncio
    async def test_incomplete_context_returns_none(self):
        # Missing access token
        ctx = SharpContext(fhir_server_url="https://fhir.example.com/r4", patient_id="p-42")
        result = await fetch_patient_context(ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_patient_id_returns_none(self):
        ctx = SharpContext(
            fhir_server_url="https://fhir.example.com/r4",
            fhir_access_token="Bearer token",
        )
        result = await fetch_patient_context(ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_patient_not_found_returns_none(self):
        ctx = SharpContext(
            fhir_server_url="https://fhir.example.com/r4",
            fhir_access_token="Bearer token",
            patient_id="nonexistent",
        )

        with patch("mcp_server.fhir_client.FHIRClient") as mock_fhir_cls:
            mock_fhir = mock_fhir_cls.return_value
            mock_fhir.get_patient = AsyncMock(return_value=None)

            result = await fetch_patient_context(ctx)

        assert result is None

    @pytest.mark.asyncio
    async def test_partial_data_still_returns(self):
        """Patient found but no conditions/medications — still returns context."""
        ctx = SharpContext(
            fhir_server_url="https://fhir.example.com/r4",
            fhir_access_token="Bearer token",
            patient_id="p-42",
        )

        with patch("mcp_server.fhir_client.FHIRClient") as mock_fhir_cls:
            mock_fhir = mock_fhir_cls.return_value
            mock_fhir.get_patient = AsyncMock(return_value=FHIR_PATIENT)
            mock_fhir.get_conditions = AsyncMock(return_value=[])
            mock_fhir.get_medications = AsyncMock(return_value=[])

            result = await fetch_patient_context(ctx)

        assert result is not None
        assert "Nguyen Van An" in result
        assert "No active conditions" in result
        assert "No active medications" in result
