"""HTTP client for the AI Engine backend."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from mcp_server.config import AI_ENGINE_BASE_URL

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(timeout=120.0, connect=10.0)


class AIEngineError(Exception):
    """Wraps errors from the AI Engine so tools return structured responses."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AIEngineClient:
    """Thin async HTTP wrapper around the AI Engine REST API."""

    def __init__(self, base_url: str = AI_ENGINE_BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")

    async def post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        """Send a POST request to the AI Engine and return the JSON response."""
        return await self._request("POST", path, json=json)

    async def get(self, path: str) -> dict[str, Any]:
        """Send a GET request to the AI Engine and return the JSON response."""
        return await self._request("GET", path)

    async def post_multipart(
        self,
        path: str,
        *,
        file_name: str,
        file_bytes: bytes,
        content_type: str = "audio/mpeg",
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Upload a file via multipart/form-data POST to the AI Engine."""
        url = f"{self._base_url}{path}"
        files = {"file": (file_name, file_bytes, content_type)}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(url, files=files, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.TimeoutException as exc:
            logger.error("AI Engine timeout: POST %s — %s", url, exc)
            raise AIEngineError("AI engine timeout", status_code=504) from exc
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            logger.error("AI Engine HTTP %d: POST %s", code, url)
            raise AIEngineError(f"AI engine returned HTTP {code}", status_code=code) from exc
        except httpx.HTTPError as exc:
            logger.error("AI Engine connection error: POST %s — %s", url, exc)
            raise AIEngineError(f"AI engine connection error: {exc}") from exc

    async def _request(
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.request(method, url, json=json)
                resp.raise_for_status()
                return resp.json()
        except httpx.TimeoutException as exc:
            logger.error("AI Engine timeout: %s %s — %s", method, url, exc)
            raise AIEngineError("AI engine timeout", status_code=504) from exc
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            logger.error("AI Engine HTTP %d: %s %s", code, method, url)
            raise AIEngineError(f"AI engine returned HTTP {code}", status_code=code) from exc
        except httpx.HTTPError as exc:
            logger.error("AI Engine connection error: %s %s — %s", method, url, exc)
            raise AIEngineError(f"AI engine connection error: {exc}") from exc
