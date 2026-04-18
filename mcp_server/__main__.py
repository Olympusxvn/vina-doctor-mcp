"""Entry point: ``python -m mcp_server``."""

from __future__ import annotations

from mcp_server.config import MCP_HOST, MCP_PORT, MCP_TRANSPORT
from mcp_server.server import mcp


def main() -> None:
    if MCP_TRANSPORT == "streamable-http":
        mcp.run(transport="streamable-http", host=MCP_HOST, port=MCP_PORT)
    else:
        mcp.run(transport="stdio")


main()
