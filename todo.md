# vina-doctor-mcp — TODO

## Phase 1 — Scaffolding ✅
- [x] Folder structure `mcp_server/` with pyproject.toml
- [x] FastMCP server with `ping()` tool
- [x] `config.py`, `sharp.py`, `ai_engine_client.py` stubs
- [x] Dockerfile + .env.example
- [x] Tests pass, ruff clean, stdio verified

## Phase 2 — Transport & SHARP ✅
- [x] Add `streamable-http` transport on port 8002
- [x] Implement `SharpContext.from_headers()` integration with request context
- [x] FHIR context discovery in `initialize` response (`ai.promptopinion/fhir-context`)
- [x] Verify: curl `initialize` sees extension declaration
- [x] Graceful degradation when FHIR headers missing (NOT 403)

## Phase 3 — 2 text-in tools ✅
- [x] `analyze_transcript` tool + `POST /v1/consultations/analyze-transcript` endpoint
- [x] `suggest_icd10` tool + `POST /v1/icd10/suggest` endpoint
- [x] Unit tests with mocked AI Engine (17 tests pass)
- [ ] Manual test with Vietnamese transcript

## Phase 4 — 4 remaining tools ✅
- [x] `generate_soap_report` (SHARP context — fhir_context_used flag, graceful degradation)
- [x] `summarize_for_patient` (JSON string input, target_language, reading_level)
- [x] `process_audio_url` (download audio → multipart upload to AI Engine)
- [x] `get_consultation_status` (poll async job status)
- [x] Unit tests (31 total, all pass)
- [ ] AI Engine endpoints (separate repo — vina-doctor)

## Phase 5 — FHIR integration ✅
- [x] `fhir_client.py` — FHIRClient fetches Patient/{id}, Condition, MedicationStatement
- [x] Patient context formatted as plain-text summary for clinical prompt injection
- [x] `generate_soap_report` enriches payload with `patient_context` when FHIR available
- [x] Graceful degradation: FHIR errors logged, tool continues without enrichment
- [x] 21 FHIR tests (demographics, conditions, medications, fetch_patient_context, error cases)
- [x] Total: 52 tests all pass
- [ ] Test with live FHIR sandbox (hapi.fhir.org) — requires AI Engine running

## Phase 6 — Deploy & Publish
- [ ] Add `mcp_server` service to docker-compose.yml
- [ ] nginx location `/mcp/` config
- [ ] GitHub Actions CI job for mcp_server
- [ ] Deploy to GCP, publish on Prompt Opinion Marketplace

## Phase 7 — Demo video
- [ ] Record < 3 min demo video
- [ ] Submit on Devpost by 11 May 2026
