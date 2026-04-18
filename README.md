# vina-doctor-mcp

MCP server that exposes [vina-doctor](https://github.com/sotaworksvn/vina-doctor) medical AI capabilities as tools for the [Prompt Opinion](https://promptopinion.ai/) platform.

## Architecture

```
MCP client (Prompt Opinion agent)
    │
    │ MCP protocol (JSON-RPC over streamable-http)
    │ Headers: X-FHIR-Server-URL, X-FHIR-Access-Token, X-Patient-ID
    ▼
┌───────────────────────────┐
│    vina-doctor MCP         │   ← this project
│  - tool registry           │
│  - SHARP header extraction │
│  - HTTP client to AI Engine│
└───────────┬────────────────┘
            │ REST (JSON)
            ▼
┌───────────────────────────┐
│    AI Engine (existing)    │
│  - ScribeAgent             │
│  - ClinicalAgent           │
│  - ICD10SelectorAgent      │
└───────────────────────────┘
```

Thin HTTP proxy — no business logic. Translates MCP tool calls into AI Engine REST requests.

## Tools (planned)

| Tool | Description | FHIR |
|---|---|---|
| `analyze_transcript` | Transcript → SOAP + ICD-10 + multilingual | No |
| `suggest_icd10` | Clinical text → ICD-10 code suggestions | No |
| `generate_soap_report` | Transcript → full multilingual SOAP report | Optional |
| `summarize_for_patient` | Clinical report → patient-friendly summary | No |
| `process_audio_url` | Audio URL → full pipeline → SOAP report | Optional |
| `get_consultation_status` | Poll async job status | No |

## Quick start

```bash
cd mcp_server
uv sync --extra dev

# Run on stdio (local dev / MCP Inspector)
uv run python -m mcp_server

# Run on streamable-http (production)
MCP_TRANSPORT=streamable-http uv run python -m mcp_server

# Lint & test
uv run ruff check . && uv run ruff format --check .
uv run pytest tests/ -v
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `AI_ENGINE_BASE_URL` | `http://ai_engine:8000` | AI Engine REST URL |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `streamable-http` |
| `MCP_HOST` | `0.0.0.0` | Bind host (streamable-http only) |
| `MCP_PORT` | `8002` | Bind port (streamable-http only) |

## SHARP-on-MCP

Follows [SHARP spec](https://sharponmcp.com/) for FHIR context propagation via HTTP headers. Tools that support FHIR context will use patient data when available, and gracefully degrade when headers are absent.

## Hackathon

**Agents Assemble — The Healthcare AI Endgame** (Prompt Opinion)
- Deadline: 11 May 2026
- Repo: github.com/olympusxvn/vina-doctor-mcp

## License

Apache-2.0
