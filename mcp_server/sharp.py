"""SHARP-on-MCP — extract and validate FHIR context from HTTP headers."""

from __future__ import annotations

from pydantic import BaseModel


class SharpContext(BaseModel):
    """FHIR context propagated via SHARP HTTP headers."""

    fhir_server_url: str | None = None
    fhir_access_token: str | None = None
    patient_id: str | None = None

    @classmethod
    def from_headers(cls, headers: dict) -> SharpContext:
        return cls(
            fhir_server_url=headers.get("X-FHIR-Server-URL"),
            fhir_access_token=headers.get("X-FHIR-Access-Token"),
            patient_id=headers.get("X-Patient-ID"),
        )

    @property
    def is_complete(self) -> bool:
        """True when both FHIR server URL and access token are present."""
        return bool(self.fhir_server_url and self.fhir_access_token)
