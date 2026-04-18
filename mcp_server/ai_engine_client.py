"""HTTP client for the AI Engine backend."""

from __future__ import annotations

from typing import Any

import httpx

from mcp_server.config import AI_ENGINE_BASE_URL

_TIMEOUT = httpx.Timeout(timeout=120.0, connect=10.0)


class AIEngineClient:
    """Thin async HTTP wrapper around the AI Engine REST API."""

    def __init__(self, base_url: str = AI_ENGINE_BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")

    async def post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        """Send a POST request to the AI Engine and return the JSON response."""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{self._base_url}{path}", json=json)
            resp.raise_for_status()
            return resp.json()

    async def get(self, path: str) -> dict[str, Any]:
        """Send a GET request to the AI Engine and return the JSON response."""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{self._base_url}{path}")
            resp.raise_for_status()
            return resp.json()
