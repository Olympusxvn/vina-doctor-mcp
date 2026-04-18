"""Tests for SHARP-on-MCP context extraction."""

from __future__ import annotations

from unittest.mock import MagicMock

from mcp_server.sharp import SharpContext, get_sharp_context


class TestSharpContextFromHeaders:
    def test_full_headers(self):
        headers = {
            "x-fhir-server-url": "https://fhir.example.com/r4",
            "x-fhir-access-token": "Bearer abc123",
            "x-patient-id": "patient-42",
        }
        ctx = SharpContext.from_headers(headers)
        assert ctx.fhir_server_url == "https://fhir.example.com/r4"
        assert ctx.fhir_access_token == "Bearer abc123"
        assert ctx.patient_id == "patient-42"
        assert ctx.is_complete is True

    def test_missing_all_headers(self):
        ctx = SharpContext.from_headers({})
        assert ctx.fhir_server_url is None
        assert ctx.fhir_access_token is None
        assert ctx.patient_id is None
        assert ctx.is_complete is False

    def test_partial_headers_not_complete(self):
        headers = {"x-fhir-server-url": "https://fhir.example.com/r4"}
        ctx = SharpContext.from_headers(headers)
        assert ctx.fhir_server_url == "https://fhir.example.com/r4"
        assert ctx.fhir_access_token is None
        assert ctx.is_complete is False

    def test_patient_id_optional(self):
        headers = {
            "x-fhir-server-url": "https://fhir.example.com/r4",
            "x-fhir-access-token": "Bearer token",
        }
        ctx = SharpContext.from_headers(headers)
        assert ctx.is_complete is True
        assert ctx.patient_id is None


class TestGetSharpContext:
    def test_extracts_from_http_request(self):
        mock_request = MagicMock()
        mock_request.headers = {
            "x-fhir-server-url": "https://fhir.example.com/r4",
            "x-fhir-access-token": "Bearer token",
            "x-patient-id": "p-1",
        }
        mock_ctx = MagicMock()
        mock_ctx.request_context.request = mock_request

        ctx = get_sharp_context(mock_ctx)
        assert ctx.fhir_server_url == "https://fhir.example.com/r4"
        assert ctx.patient_id == "p-1"
        assert ctx.is_complete is True

    def test_returns_empty_when_no_request(self):
        mock_ctx = MagicMock()
        mock_ctx.request_context.request = None

        ctx = get_sharp_context(mock_ctx)
        assert ctx.is_complete is False
        assert ctx.fhir_server_url is None

    def test_returns_empty_on_attribute_error(self):
        mock_ctx = MagicMock(spec=[])  # no attributes

        ctx = get_sharp_context(mock_ctx)
        assert ctx.is_complete is False
