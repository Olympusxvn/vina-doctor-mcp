"""SHARP-on-MCP — extract and validate FHIR context from HTTP headers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from mcp.server.fastmcp import Context

logger = logging.getLogger(__name__)


class SharpContext(BaseModel):
    """FHIR context propagated via SHARP HTTP headers."""

    fhir_server_url: str | None = None
    fhir_access_token: str | None = None
    patient_id: str | None = None

    @classmethod
    def from_headers(cls, headers: dict) -> SharpContext:
        return cls(
            fhir_server_url=headers.get("x-fhir-server-url"),
            fhir_access_token=headers.get("x-fhir-access-token"),
            patient_id=headers.get("x-patient-id"),
        )

    @property
    def is_complete(self) -> bool:
        """True when both FHIR server URL and access token are present."""
        return bool(self.fhir_server_url and self.fhir_access_token)


def get_sharp_context(ctx: Context) -> SharpContext:
    """Extract SHARP context from an MCP tool call's request context.

    Returns an empty SharpContext when running on stdio (no HTTP headers)
    or when headers are absent (user opted out of FHIR context).
    """
    try:
        request = ctx.request_context.request
        if request is not None:
            return SharpContext.from_headers(dict(request.headers))
    except AttributeError:
        pass

    logger.debug("No HTTP request context — returning empty SharpContext")
    return SharpContext()
