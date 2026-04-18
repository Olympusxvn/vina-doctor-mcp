"""Shared fixtures for MCP server tests."""

from __future__ import annotations

import pytest

from mcp_server.server import mcp


@pytest.fixture
def mcp_server():
    """Return the FastMCP server instance for testing."""
    return mcp
