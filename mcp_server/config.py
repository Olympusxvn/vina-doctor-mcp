"""Configuration — reads environment variables for the MCP server."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

AI_ENGINE_BASE_URL: str = os.getenv("AI_ENGINE_BASE_URL", "http://ai_engine:8000")
MCP_TRANSPORT: str = os.getenv("MCP_TRANSPORT", "stdio")
MCP_HOST: str = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT: int = int(os.getenv("MCP_PORT", "8002"))
