FROM python:3.11-slim AS base

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml ./mcp_server/pyproject.toml

# Copy the package source
COPY . ./mcp_server/

# Install dependencies
RUN cd mcp_server && uv sync --no-dev

# Default: streamable-http transport
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8002

EXPOSE 8002

CMD ["uv", "run", "--directory", "mcp_server", "python", "-m", "mcp_server"]
