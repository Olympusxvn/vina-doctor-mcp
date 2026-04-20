"""Tests for Phase 4 tools: generate_soap_report, summarize_for_patient,
process_audio_url, get_consultation_status."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from mcp_server.ai_engine_client import AIEngineError
from mcp_server.sharp import SharpContext
from mcp_server.tools.generate_soap_report import generate_soap_report
from mcp_server.tools.get_consultation_status import get_consultation_status
from mcp_server.tools.process_audio_url import process_audio_url
from mcp_server.tools.summarize_for_patient import summarize_for_patient

# ---------------------------------------------------------------------------
# Mock responses
# ---------------------------------------------------------------------------

MOCK_SOAP_REPORT = {
    "metadata": {"primary_language": "vi", "session_id": "soap-001"},
    "transcript": [],
    "clinical_report": {
        "chief_complaint": {"en": "Cough and fever", "vn": "Ho và sốt", "fr": "", "ar": ""},
        "soap_notes": {
            "subjective": {"en": "...", "vn": "...", "fr": "", "ar": ""},
            "objective": {"en": "...", "vn": "...", "fr": "", "ar": ""},
            "assessment": {"en": "...", "vn": "...", "fr": "", "ar": ""},
            "plan": {"en": "...", "vn": "...", "fr": "", "ar": ""},
        },
        "icd10_codes": ["J06.9"],
        "severity_flag": "Low",
        "urgency_level": "Low",
    },
    "multilingual_summary": {"en": "...", "vn": "...", "fr": "", "ar": ""},
}

MOCK_PATIENT_SUMMARY = {
    "summary": "Bạn bị cảm lạnh nhẹ.",
    "summary_en": "You have a mild cold.",
    "key_actions": ["Nghỉ ngơi", "Uống nhiều nước"],
    "medications_plain": [{"name": "Paracetamol", "how_to_take": "500mg, 3 lần/ngày"}],
    "follow_up": "Tái khám sau 3 ngày nếu không đỡ.",
    "urgency_note": None,
}

MOCK_AUDIO_REPORT = {
    "metadata": {"primary_language": "vi", "session_id": "audio-001"},
    "transcript": [{"speaker": "Doctor", "text": "Chào anh"}],
    "clinical_report": {"icd10_codes": ["J06.9"]},
    "multilingual_summary": {"en": "...", "vn": "..."},
}

MOCK_STATUS = {
    "session_id": "audio-001",
    "status": "COMPLETED",
    "current_step": "ClinicalAgent",
    "result": MOCK_AUDIO_REPORT,
    "error": None,
}


# ---------------------------------------------------------------------------
# generate_soap_report
# ---------------------------------------------------------------------------


class TestGenerateSoapReport:
    @pytest.mark.asyncio
    async def test_happy_path_no_fhir(self):
        with patch("mcp_server.tools.generate_soap_report.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(return_value=MOCK_SOAP_REPORT)

            result = await generate_soap_report(transcript="Doctor: hello")

        assert result["fhir_context_used"] is False
        assert "clinical_report" in result

    @pytest.mark.asyncio
    async def test_with_fhir_context(self):
        sharp = SharpContext(
            fhir_server_url="https://fhir.example.com/r4",
            fhir_access_token="Bearer token",
            patient_id="p-42",
        )

        mock_context = "--- Patient Context (from FHIR) ---\nPatient: Test\n---"

        with (
            patch("mcp_server.tools.generate_soap_report.AIEngineClient") as mock_client_cls,
            patch(
                "mcp_server.tools.generate_soap_report.fetch_patient_context",
                new_callable=AsyncMock,
                return_value=mock_context,
            ),
        ):
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(return_value=MOCK_SOAP_REPORT)

            result = await generate_soap_report(transcript="Doctor: hello", sharp_context=sharp)

        assert result["fhir_context_used"] is True
        call_json = instance.post.call_args[1]["json"]
        assert "patient_context" in call_json
        assert "fhir_context" in call_json
        assert call_json["fhir_context"]["patient_id"] == "p-42"

    @pytest.mark.asyncio
    async def test_custom_languages(self):
        with patch("mcp_server.tools.generate_soap_report.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(return_value=MOCK_SOAP_REPORT)

            await generate_soap_report(transcript="test", output_languages=["en", "vn"])

        call_json = instance.post.call_args[1]["json"]
        assert call_json["output_languages"] == ["en", "vn"]

    @pytest.mark.asyncio
    async def test_timeout(self):
        with patch("mcp_server.tools.generate_soap_report.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(
                side_effect=AIEngineError("AI engine timeout", status_code=504)
            )

            result = await generate_soap_report(transcript="test")

        assert result["error"] == "AI engine timeout"
        assert result["retry_after"] == 30
        assert result["fhir_context_used"] is False


# ---------------------------------------------------------------------------
# summarize_for_patient
# ---------------------------------------------------------------------------


class TestSummarizeForPatient:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        report_json = json.dumps(MOCK_SOAP_REPORT["clinical_report"])

        with patch("mcp_server.tools.summarize_for_patient.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(return_value=MOCK_PATIENT_SUMMARY)

            result = await summarize_for_patient(clinical_report_json=report_json)

        assert "summary" in result
        assert result["key_actions"] == ["Nghỉ ngơi", "Uống nhiều nước"]

    @pytest.mark.asyncio
    async def test_invalid_json(self):
        result = await summarize_for_patient(clinical_report_json="not valid json{{{")

        assert "error" in result
        assert "Invalid JSON" in result["error"]

    @pytest.mark.asyncio
    async def test_custom_language_and_level(self):
        with patch("mcp_server.tools.summarize_for_patient.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(return_value=MOCK_PATIENT_SUMMARY)

            await summarize_for_patient(
                clinical_report_json="{}",
                target_language="en",
                reading_level="standard",
            )

        call_json = instance.post.call_args[1]["json"]
        assert call_json["target_language"] == "en"
        assert call_json["reading_level"] == "standard"

    @pytest.mark.asyncio
    async def test_timeout(self):
        with patch("mcp_server.tools.summarize_for_patient.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.post = AsyncMock(
                side_effect=AIEngineError("AI engine timeout", status_code=504)
            )

            result = await summarize_for_patient(clinical_report_json="{}")

        assert result["error"] == "AI engine timeout"
        assert result["retry_after"] == 30


# ---------------------------------------------------------------------------
# process_audio_url
# ---------------------------------------------------------------------------


def _mock_http_download(mock_http_cls, content: bytes = b"fake-audio-bytes"):
    """Set up mock for httpx.AsyncClient used as async context manager."""
    mock_response = AsyncMock()
    mock_response.content = content
    mock_response.raise_for_status = lambda: None
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_ctx.get = AsyncMock(return_value=mock_response)
    mock_http_cls.return_value = mock_ctx
    return mock_ctx


class TestProcessAudioUrl:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        with (
            patch("mcp_server.tools.process_audio_url.httpx.AsyncClient") as mock_http,
            patch("mcp_server.tools.process_audio_url.AIEngineClient") as mock_client_cls,
        ):
            _mock_http_download(mock_http)

            instance = mock_client_cls.return_value
            instance.post_multipart = AsyncMock(return_value=MOCK_AUDIO_REPORT)

            result = await process_audio_url(audio_url="https://example.com/consultation.mp3")

        assert "clinical_report" in result
        instance.post_multipart.assert_called_once()
        call_kwargs = instance.post_multipart.call_args[1]
        assert call_kwargs["file_name"] == "consultation.mp3"
        assert call_kwargs["content_type"] == "audio/mpeg"

    @pytest.mark.asyncio
    async def test_download_timeout(self):
        with patch("mcp_server.tools.process_audio_url.httpx.AsyncClient") as mock_http:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_http.return_value = mock_ctx

            result = await process_audio_url(audio_url="https://example.com/big.mp3")

        assert "Timeout downloading" in result["error"]

    @pytest.mark.asyncio
    async def test_file_too_large(self):
        with patch("mcp_server.tools.process_audio_url.httpx.AsyncClient") as mock_http:
            _mock_http_download(mock_http, content=b"x" * (51 * 1024 * 1024))

            result = await process_audio_url(audio_url="https://example.com/huge.mp3")

        assert "too large" in result["error"]

    @pytest.mark.asyncio
    async def test_ai_engine_500(self):
        with (
            patch("mcp_server.tools.process_audio_url.httpx.AsyncClient") as mock_http,
            patch("mcp_server.tools.process_audio_url.AIEngineClient") as mock_client_cls,
        ):
            _mock_http_download(mock_http, content=b"audio")

            instance = mock_client_cls.return_value
            instance.post_multipart = AsyncMock(
                side_effect=AIEngineError("AI engine returned HTTP 500", status_code=500)
            )

            result = await process_audio_url(audio_url="https://example.com/test.mp3")

        assert result["error"] == "AI engine returned HTTP 500"
        assert result["status_code"] == 500


# ---------------------------------------------------------------------------
# get_consultation_status
# ---------------------------------------------------------------------------


class TestGetConsultationStatus:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        with patch("mcp_server.tools.get_consultation_status.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.get = AsyncMock(return_value=MOCK_STATUS)

            result = await get_consultation_status(session_id="audio-001")

        assert result["status"] == "COMPLETED"
        assert result["session_id"] == "audio-001"
        instance.get.assert_called_once_with("/v1/consultations/audio-001/status")

    @pytest.mark.asyncio
    async def test_not_found(self):
        with patch("mcp_server.tools.get_consultation_status.AIEngineClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.get = AsyncMock(
                side_effect=AIEngineError("AI engine returned HTTP 404", status_code=404)
            )

            result = await get_consultation_status(session_id="nonexistent")

        assert result["status_code"] == 404
