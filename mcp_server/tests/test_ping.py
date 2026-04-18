"""Test the ping health-check tool."""

from __future__ import annotations

import pytest

from mcp_server.server import ping


@pytest.mark.asyncio
async def test_ping_returns_pong():
    result = await ping()
    assert result == "pong"
