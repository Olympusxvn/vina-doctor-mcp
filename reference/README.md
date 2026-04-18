# vina-doctor

A medical consultation platform that records doctor–patient audio, transcribes it with speaker diarization, and generates multilingual SOAP reports using Alibaba's Qwen AI models.

## Architecture

The project is divided into three services:

| Service | Responsibility |
|---|---|
| **frontend** | Microphone recording, audio upload, progress display, multilingual report viewer |
| **backend** | API gateway, authentication, database persistence, job orchestration |
| **ai_engine** | Audio transcription (STT + diarization), clinical analysis, SOAP report generation |

### Data flow

```
frontend  →  record audio, upload, display progress
backend   →  receive audio, create consultation job, call ai_engine
ai_engine →  VAD check, audio pre-processing (ffmpeg)
          →  ScribeAgent: Qwen2-Audio → structured transcript + diarization
          →  TextCleanerService: PII redaction
          →  ClinicalAgent: Qwen model → SOAP report + diagnostics
backend   →  persist to DB, return normalised JSON
frontend  →  render multilingual report
```

## Repository structure

```
vina-doctor/
├── ai_engine/   # FastAPI AI service — transcription + clinical analysis
├── backend/     # FastAPI backend — API, auth, DB
├── frontend/    # Next.js frontend — recording and report UI
└── docs/        # Additional documentation
```

See each sub-directory's `README.md` for setup instructions:
- [`ai_engine/README.md`](ai_engine/README.md)
- [`backend/README.md`](backend/README.md)
- [`frontend/README.md`](frontend/README.md)

## Run with Docker Compose

The repository includes a top-level `docker-compose.yml` which defines the full system topology (Postgres, ai_engine, backend, frontend, nginx). Use this file to run the entire system.

Examples:

```bash
# Development (build locally):
docker compose up --build

# Production (pull published images and start detached):
docker compose pull && docker compose up -d
```

Ensure you have a `.env` file populated (copy from `.env.example`) before starting.