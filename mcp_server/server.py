"""FastMCP server — tool registration and transport entry point."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "vina-doctor",
    instructions=(
        "Medical AI toolkit powered by vina-doctor. "
        "Provides tools for clinical transcript analysis, SOAP report generation, "
        "ICD-10 code suggestion, patient-friendly summaries, and audio processing. "
        "Supports multilingual output (EN, VN, FR, AR)."
    ),
)


@mcp.tool()
async def ping() -> str:
    """Health-check tool. Returns 'pong' to verify MCP connectivity."""
    return "pong"
