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
