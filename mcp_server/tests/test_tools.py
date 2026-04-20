"""Tests for analyze_transcript and suggest_icd10 MCP tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mcp_server.ai_engine_client import AIEngineError
from mcp_server.tools.analyze_transcript import analyze_transcript
from mcp_server.tools.suggest_icd10 import suggest_icd10

# ---------------------------------------------------------------------------
# Fixtures — mock AI Engine responses
# ---------------------------------------------------------------------------

MOCK_MEDICAL_REPORT = {
    "metadata": {
        "primary_language": "vi",
        "session_id": "test-session-001",
    },
    "transcript": [],
    "clinical_report": {
        "chief_complaint": {"en": "Headache", "vn": "Đau đầu", "fr": "", "ar": ""},
        "soap_notes": {
            "subjective": {"en": "Patient reports headache", "vn": "...", "fr": "", "ar": ""},
            "objective": {"en": "BP 120/80", "vn": "...", "fr": "", "ar": ""},
            "assessment": {"en": "Tension headache", "vn": "...", "fr": "", "ar": ""},
            "plan": {"en": "Rest and analgesics", "vn": "...", "fr": "", "ar": ""},
        },
        "medications": [{"name": "Paracetamol", "dosage": "500mg"}],
        "icd10_codes": ["G44.1"],
        "severity_flag": "Low",
        "urgency_level": "Low",
    },
    "multilingual_summary": {
        "en": "Patient has tension headache",
        "vn": "Bệnh nhân bị đau đầu căng thẳng",
        "fr": "",
        "ar": "",
    },
}

MOCK_ICD10_RESPONSE = {
    "suggestions": [
        {
            "code": "J06.9",
            "description": "Acute upper respiratory infection, unspecified",
            "confidence": 0.82,
            "category": "respiratory",
        },
        {
            "code": "J20.9",
            "description": "Acute bronchitis, unspecified",
            "confidence": 0.65,
            "category": "respiratory",
        },
    ],
    "primary": {
        "code": "J06.9",
        "description": "Acute upper respiratory infection, unspecified",
        "confidence": 0.82,
        "category": "respiratory",
    },
}


# ---------------------------------------------------------------------------
# analyze_transcript tests
# ---------------------------------------------------------------------------


class TestAnalyzeTranscript:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        with patch("mcp_server.tools.analyze_transcript.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(return_value=MOCK_MEDICAL_REPORT)

            result = await analyze_transcript(
                transcript="Bác sĩ: Chào anh. Anh bị đau đầu bao lâu rồi?",
                language_hint="vi",
            )

        assert "clinical_report" in result
        assert result["clinical_report"]["icd10_codes"] == ["G44.1"]
        instance.post.assert_called_once_with(
            "/v1/consultations/analyze-transcript",
            json={
                "transcript": "Bác sĩ: Chào anh. Anh bị đau đầu bao lâu rồi?",
                "language_hint": "vi",
            },
        )

    @pytest.mark.asyncio
    async def test_default_language_hint(self):
        with patch("mcp_server.tools.analyze_transcript.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(return_value=MOCK_MEDICAL_REPORT)

            await analyze_transcript(transcript="Doctor: Hello.")

        instance.post.assert_called_once_with(
            "/v1/consultations/analyze-transcript",
            json={"transcript": "Doctor: Hello.", "language_hint": "auto"},
        )

    @pytest.mark.asyncio
    async def test_ai_engine_timeout(self):
        with patch("mcp_server.tools.analyze_transcript.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(
                side_effect=AIEngineError("AI engine timeout", status_code=504)
            )

            result = await analyze_transcript(transcript="test")

        assert result["error"] == "AI engine timeout"
        assert result["status_code"] == 504
        assert result["retry_after"] == 30

    @pytest.mark.asyncio
    async def test_ai_engine_500(self):
        with patch("mcp_server.tools.analyze_transcript.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(
                side_effect=AIEngineError("AI engine returned HTTP 500", status_code=500)
            )

            result = await analyze_transcript(transcript="test")

        assert result["error"] == "AI engine returned HTTP 500"
        assert result["status_code"] == 500
        assert "retry_after" not in result


# ---------------------------------------------------------------------------
# suggest_icd10 tests
# ---------------------------------------------------------------------------


class TestSuggestIcd10:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        with patch("mcp_server.tools.suggest_icd10.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(return_value=MOCK_ICD10_RESPONSE)

            result = await suggest_icd10(
                clinical_text="Patient presents with sore throat and cough",
                max_suggestions=3,
            )

        assert "suggestions" in result
        assert len(result["suggestions"]) == 2
        assert result["primary"]["code"] == "J06.9"
        instance.post.assert_called_once_with(
            "/v1/icd10/suggest",
            json={
                "clinical_text": "Patient presents with sore throat and cough",
                "max_suggestions": 3,
            },
        )

    @pytest.mark.asyncio
    async def test_max_suggestions_clamped(self):
        with patch("mcp_server.tools.suggest_icd10.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(return_value=MOCK_ICD10_RESPONSE)

            await suggest_icd10(clinical_text="test", max_suggestions=99)

        call_json = instance.post.call_args[1]["json"]
        assert call_json["max_suggestions"] == 10

    @pytest.mark.asyncio
    async def test_max_suggestions_minimum(self):
        with patch("mcp_server.tools.suggest_icd10.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(return_value=MOCK_ICD10_RESPONSE)

            await suggest_icd10(clinical_text="test", max_suggestions=0)

        call_json = instance.post.call_args[1]["json"]
        assert call_json["max_suggestions"] == 1

    @pytest.mark.asyncio
    async def test_ai_engine_timeout(self):
        with patch("mcp_server.tools.suggest_icd10.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(
                side_effect=AIEngineError("AI engine timeout", status_code=504)
            )

            result = await suggest_icd10(clinical_text="test")

        assert result["error"] == "AI engine timeout"
        assert result["retry_after"] == 30

    @pytest.mark.asyncio
    async def test_ai_engine_500(self):
        with patch("mcp_server.tools.suggest_icd10.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(
                side_effect=AIEngineError("AI engine returned HTTP 500", status_code=500)
            )

            result = await suggest_icd10(clinical_text="test")

        assert result["error"] == "AI engine returned HTTP 500"
        assert result["status_code"] == 500
