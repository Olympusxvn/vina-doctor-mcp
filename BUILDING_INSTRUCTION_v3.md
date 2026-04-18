# Building Instruction: vina-doctor-mcp

> **Version 3** — 19 April 2026
> **Target executor:** Claude Code
> **Target reviewer (you):** human PM / developer
> **Role of Claude (advisor):** spec the work, answer questions, review PRs
> **Deadline:** 11 May 2026 (hackathon submission)
> **Hackathon:** Agents Assemble — The Healthcare AI Endgame (Prompt Opinion)
> **Repo:** https://github.com/sotaworksvn/vina-doctor
> **Live (for judges):** https://vina-doctor.serveousercontent.com/
> **Platform docs:** https://docs.promptopinion.ai/

### Changelog v2 → v3 (THAY ĐỔI LỚN)

Sau khi đọc Prompt Opinion docs chính thức (docs.promptopinion.ai) và repo mới, các điều chỉnh so với v2:

- **§3.5, §6**: Extension spec đổi từ `capabilities.experimental.fhir_context_required` sang `capabilities.extensions["ai.promptopinion/fhir-context"]`. Spec SHARP cũ (sharponmcp.com) KHÔNG phải là spec Prompt Opinion dùng. Claude Code phải theo Prompt Opinion spec.
- **§6.4**: Khi MCP thiếu FHIR headers — KHÔNG trả 403. User có thể opt-out. Tool phải graceful degradation.
- **§3.1, §8**: Chính thức chọn `ai_engine/` làm core backend cho MCP (không phải `mr_cuong_ai_engine/` — đó là R&D sandbox, chưa có FastAPI service). Mapping tool → endpoint có sẵn trong `ai_engine/`.
- **§12**: `mr_cuong_ai_engine/` là core R&D (prompt thế hệ mới), **không đụng từ MCP side**. Khi Cường merge prompts vào `ai_engine/`, MCP tự động hưởng lợi.
- **§10.6**: Team sẽ làm HTTPS trên Google Cloud (không phải Alibaba ECS, không phải Cloudflare). Ghi chú handoff.

### Changelog v1 → v2

- §4: Repository layout cập nhật theo cấu trúc thực (có `nginx/`, `scripts/`, `mr_cuong_ai_engine/`, `.specify/`, `Dockerfile` ở root cho ai_engine).
- §3.5: Sơ đồ kiến trúc thêm nginx làm reverse proxy — MCP sẽ được route qua `/mcp/`.
- §10: Deployment dùng GHCR + GitHub Actions workflow "Deploy to ECS" hiện có.
- §15 (MỚI): Team coordination & git workflow.

---

## 0. TL;DR

Chúng ta nâng cấp `vina-doctor` (medical scribe hiện có) thành `vina-doctor-mcp` — một **MCP server** expose các khả năng y tế của AI Engine ra dưới dạng tools, tuân thủ **SHARP-on-MCP** spec để agent bất kỳ trên nền tảng **Prompt Opinion** đều có thể gọi được.

**Path chọn:** Option 1 — "Superpower" (MCP server) — *không* phải Option 2 (A2A agent).

**Không build lại AI Engine.** Code ML/LLM giữ nguyên. MCP server là một service mới, mỏng, chạy song song, chuyển request MCP → HTTP → AI Engine.

---

## 1. Context cho người đọc

### 1.1. vina-doctor hiện tại (recap)

Monorepo 3 service Docker Compose:

| Service | Stack | Chức năng |
|---|---|---|
| `frontend/` | Next.js 16 | Record audio, upload, xem báo cáo đa ngôn ngữ |
| `backend/` | FastAPI + SQLAlchemy + Alembic | API gateway, auth, DB |
| `ai_engine/` | FastAPI + DashScope (Qwen3.5-Omni-Flash) | Transcribe, diarization, PII redaction, SOAP generation |

AI Engine có sẵn 2 agent:
- `ScribeAgent`: audio → structured transcript (diarization)
- `ClinicalAgent`: transcript → SOAP + ICD-10 + đa ngôn ngữ EN/VN/FR/AR

### 1.2. Hackathon yêu cầu gì

- Build MCP server expose tools y tế.
- Tuân thủ **SHARP-on-MCP** cho việc truyền context (patient ID + FHIR token) qua HTTP headers.
- Khuyến nghị (không bắt buộc) có tương tác với FHIR server.
- Publish lên Prompt Opinion Marketplace.
- Demo video < 3 phút cho thấy tool được gọi từ Prompt Opinion platform.

### 1.3. Tiêu chí chấm

1. **AI Factor** — Generative AI giải quyết được việc rule-based không làm được.
2. **Potential Impact** — pain point rõ, giả thuyết cải thiện outcomes/cost/time.
3. **Feasibility** — chạy được trong hệ thống y tế thực, tôn trọng privacy/safety/regulation.

---

## 2. Scope

### 2.1. In-scope (phải có)

- Dịch vụ mới `mcp_server/` trong cùng repo.
- 6 MCP tools (chi tiết ở §5).
- **SHARP-on-MCP compliance**: 3 HTTP headers chuẩn, FHIR context discovery qua `initialize` response.
- 2 transport: `stdio` (dev/local) và `streamable-http`/`sse` (deploy cho Prompt Opinion).
- Bổ sung 3 endpoint REST mới vào `ai_engine/` để MCP server gọi vào (chi tiết ở §8).
- Docker image riêng cho MCP server.
- Publish lên Prompt Opinion Marketplace.
- Demo video.

### 2.2. Out-of-scope (lần này *không* làm)

- Không sửa `backend/` hay `frontend/`. Chúng vẫn chạy như cũ.
- Không đổi Qwen model, không đổi prompt, không retrain.
- Không build FHIR server riêng. MCP server chỉ **consume** FHIR khi token được cung cấp qua header.
- Không làm write-back FHIR (chỉ đọc, không ghi) — để tránh rủi ro về compliance/testing.
- Không làm A2A agent (đó là Option 2, mình không chọn).
- Không làm ứng dụng web mới; Prompt Opinion chính là UI host.

### 2.3. Nice-to-have (nếu còn thời gian)

- FHIR `Observation` write-back (ghi SOAP assessment về FHIR).
- Audit log qua `AuditEvent` FHIR resource.
- Thêm tool `fetch_patient_history` (đọc `Condition`/`MedicationStatement` từ FHIR để tăng ngữ cảnh cho SOAP).

---

## 3. Quyết định kiến trúc

> **Cần bạn confirm các điểm đánh dấu 🔶 trước khi Claude Code bắt đầu.**

### 3.1. 🔶 Relationship giữa MCP server và AI Engine

**Khuyến nghị:** MCP server là **HTTP proxy mỏng** gọi vào AI Engine qua REST.

| Option | Ưu | Nhược |
|---|---|---|
| **A. HTTP proxy (khuyến nghị)** | Triển khai độc lập, không đụng đến AI Engine deployment, dễ scale, dễ host MCP ở nơi khác (Prompt Opinion registry) | Phải thêm 3 endpoint REST vào AI Engine |
| B. In-process import | Bớt 1 hop mạng, latency thấp hơn chút | Coupling chặt, MCP server phải có model weights, deployment phức tạp hơn |

**→ Đề xuất chọn A.** Tất cả instruction dưới đây giả định A.

### 3.1.1. CHÍNH THỨC CHỌN `ai_engine/` LÀ BACKEND CHO MCP

Trong repo có 2 folder có vẻ giống nhau:

| Folder | Vai trò | Dùng cho MCP? |
|---|---|---|
| **`ai_engine/`** | ✅ Production engine — full Clean Architecture, có FastAPI, đang chạy port 8000, đang serve cho `vina-doctor.serveousercontent.com` | ✅ **ĐÚNG** |
| `mr_cuong_ai_engine/` | 🟡 R&D sandbox — các file Python rời rạc, `main.py` chỉ là "Hello from ai-engine!", chưa có FastAPI, không có trong docker-compose. Chứa các `MASTER_*_PROMPT.md` là design spec cho prompt thế hệ mới | ❌ Không — chưa chạy được |

**Lý do chọn `ai_engine/`:**
1. **Nó đang chạy** — giám khảo đã test được tại `vina-doctor.serveousercontent.com`.
2. **Nó có API** — `/v1/consultations/*` và `/v1/config/*` đã có sẵn.
3. **Nó có đầy đủ agent** — ScribeAgent, ClinicalAgent, ICD10SelectorAgent, MedicalExtractor, MedicalReporter.
4. **Tiết kiệm thời gian** — không cần đợi Cường lắp ráp `mr_cuong_ai_engine/` thành service.

**Vai trò tương lai của `mr_cuong_ai_engine/`:**
- Là nơi Cường tinh chỉnh prompts thế hệ mới (MASTER_CLINICAL_AGENT_PROMPT.md, MASTER_MEDICAL_SCRIBE_PROMPT.md).
- Khi xong, các prompt mới này sẽ **merge vào `ai_engine/agents/clinical_prompts.py` và `scribe_prompts.py`** (file-level replacement).
- MCP server **không đổi gì** khi điều đó xảy ra. Vì MCP chỉ là proxy HTTP, không biết/không quan tâm prompt bên trong `ai_engine/` như thế nào.

### 3.1.2. Endpoints sẵn có trong `ai_engine/`

MCP tool sẽ map sang các endpoint có sẵn + một số endpoint mới:

| MCP tool | AI Engine endpoint | Status |
|---|---|---|
| `process_audio_url` | `POST /v1/consultations/process` (cần thêm variant nhận URL) | Cần thêm |
| `generate_soap_report` (từ transcript) | `POST /v1/consultations/process-v2` (cần variant text-only) | Cần thêm |
| `analyze_transcript` | `POST /v1/consultations/analyze-transcript` | **MỚI** |
| `suggest_icd10` | `POST /v1/icd10/suggest` | **MỚI** |
| `summarize_for_patient` | `POST /v1/consultations/patient-summary` | **MỚI** |
| `get_consultation_status` | `GET /v1/consultations/{session_id}/status` | Đã có |

Có `ICD10SelectorAgent` sẵn trong code — dùng lại để implement `POST /v1/icd10/suggest` nhanh chóng (xem `ai_engine/agents/icd10_selector_agent.py`).

### 3.2. 🔶 Ngôn ngữ & SDK

**Khuyến nghị:** **Python 3.11+** với SDK chính thức `mcp[cli]>=1.3.0`.

- Đồng nhất với phần còn lại của repo (AI Engine + Backend đều Python).
- Prompt Opinion có reference implementation bằng `.NET` và `Typescript`; Python không có — nhưng SDK Python MCP chính thức của Anthropic đã stable, dùng được.
- Dùng `uv` để quản lý deps (giống service khác).

### 3.3. 🔶 Transport

- **Dev/local**: `stdio` — test với Claude Desktop hoặc MCP Inspector.
- **Production (Prompt Opinion)**: `streamable-http` (MCP spec mới, khuyến nghị 2025+) — hoặc `sse` nếu platform yêu cầu.
- Check yêu cầu chính xác của Prompt Opinion trước khi code (xem §13 Open Questions).

### 3.4. SHARP context passing

- **KHÔNG** nhận SHARP context qua tool parameters.
- **PHẢI** nhận qua HTTP headers theo SHARP spec:
  - `X-FHIR-Server-URL`
  - `X-FHIR-Access-Token`
  - `X-Patient-ID` (optional)
- Implement FHIR context discovery trong `initialize` response: `capabilities.experimental.fhir_context_required.value = true`.
- Nếu client không gửi headers mà tool lại cần → trả `403 Forbidden`.
- Có tool nhận context, có tool không — phải đánh dấu rõ trong schema.

### 3.5. Separation of concerns

```
Internet  (https://47.238.224.19 or domain)
    │
    ▼
┌───────────────────────────┐
│        nginx:80            │   ← giữ nguyên, thêm 1 location
│   /          → frontend    │
│   /api/      → backend     │
│   /v1/       → ai_engine   │
│   /mcp/      → mcp_server  │   ← MỚI
└───────────┬────────────────┘
            │
            ▼
MCP client (Prompt Opinion agent)
        │
        │ MCP protocol (JSON-RPC over streamable-http)
        │ Headers: X-FHIR-Server-URL, X-FHIR-Access-Token, X-Patient-ID
        ▼
┌───────────────────────────┐
│    vina-doctor MCP         │   ← build mới
│  - tool registry           │
│  - SHARP header extraction │
│  - HTTP client to AI Engine│
└───────────┬────────────────┘
            │ REST (JSON) — Docker internal DNS
            │ AI_ENGINE_URL=http://ai_engine:8000
            ▼
┌───────────────────────────┐
│    AI Engine (existing)    │  ← thêm 3 endpoints mới
│  - ScribeAgent             │
│  - ClinicalAgent           │
│  - NEW: analyze-transcript │
│  - NEW: icd10/suggest      │
│  - NEW: patient-summary    │
└───────────┬────────────────┘
            │
            ▼  DashScope (Qwen3.5-Omni-Flash)
```

MCP server **không** chứa business logic y tế. Nó chỉ: (1) parse request, (2) validate SHARP context nếu cần, (3) gọi AI Engine, (4) format kết quả, (5) echo SHARP context vào response để agent chain có thể dùng lại.

---

## 4. Repository layout

Cấu trúc **thực tế hiện có** trên `main`:

```
vina-doctor/
├── .github/                      ← GitHub Actions + instructions docs
│   ├── instructions/
│   │   ├── clean-architecture.instructions.md
│   │   ├── solid-principles.instructions.md
│   │   └── agent-engineering.instructions.md
│   └── workflows/
│       ├── ci.yml                ← lint/test
│       └── deploy-to-ecs.yml     ← auto-deploy khi merge main
├── .specify/                     ← spec-driven dev artifacts (team đang dùng Spec Kit)
├── ai_engine/                    ← FastAPI AI service (giữ nguyên, THÊM 3 endpoint)
├── backend/                      ← FastAPI backend (KHÔNG đụng)
├── frontend/                     ← Next.js (KHÔNG đụng)
├── mr_cuong_ai_engine/           ← ⚠️ nhánh thử của Cường, KHÔNG nằm trong compose, BỎ QUA
├── nginx/
│   └── nginx.conf                ← THÊM location /mcp/
├── scripts/                      ← deploy scripts — có thể cần cập nhật
├── docs/                         ← THÊM mcp-server.md
├── AGENTS.md                     ← team conventions
├── Dockerfile                    ← ⚠️ Dockerfile này là của ai_engine (context: .)
├── docker-compose.yml            ← THÊM service mcp_server
├── .env.example                  ← THÊM biến MCP_*
├── .dockerignore
└── LICENSE                       ← Apache-2.0
```

**Cấu trúc MỚI cần thêm vào:**

```
vina-doctor/
└── mcp_server/                   ← MỚI
    ├── mcp_server/
    │   ├── __init__.py
    │   ├── server.py             ← FastMCP app, tool registration
    │   ├── config.py             ← env vars
    │   ├── sharp.py              ← SHARP header extraction + validation
    │   ├── ai_engine_client.py   ← httpx client to AI Engine
    │   └── tools/
    │       ├── __init__.py
    │       ├── analyze_transcript.py
    │       ├── suggest_icd10.py
    │       ├── generate_soap_report.py
    │       ├── summarize_for_patient.py
    │       ├── process_audio_url.py
    │       └── get_consultation_status.py
    ├── tests/
    │   ├── __init__.py
    │   ├── test_sharp.py
    │   ├── test_tools.py
    │   └── conftest.py           ← mock AI Engine
    ├── Dockerfile                ← mcp_server's own Dockerfile (không dùng root Dockerfile)
    ├── pyproject.toml
    ├── README.md
    └── .env.example
```

### 4.1. Quirk cần biết về Python package structure

Theo AGENTS.md: mỗi service dùng `package-dir = {"" = ".."}` nghĩa là service dir **chính là package**. MCP server sẽ làm tương tự:
- Import từ repo root: `from mcp_server.server import mcp`
- **KHÔNG** tạo layout `src/`
- Chạy `uv sync` từ trong `mcp_server/` khi thêm deps

### 4.2. Dockerfile convention

`Dockerfile` ở repo root là của `ai_engine` (vì `context: .`). MCP server cần Dockerfile riêng tại `mcp_server/Dockerfile` với `context: ./mcp_server` trong compose. Đây là pattern đã dùng cho `backend/` và `frontend/` — follow theo.

---

## 5. MCP Tools — Specification

6 tools. Tool nào cần FHIR context được đánh dấu 🔒. Tool không cần đánh dấu 🔓.

### 5.1. 🔓 `analyze_transcript`

**Mục đích:** Phân tích một transcript (text) đã có sẵn, trả về SOAP + ICD-10 + đa ngôn ngữ.

**Input:**
```json
{
  "transcript": "string (raw text, có thể multilingual, có dialog turn)",
  "language_hint": "'vi' | 'en' | 'fr' | 'ar' | 'auto'"
}
```

**Output:** Cấu trúc `MedicalReport` (metadata, clinical_report, multilingual_summary) — copy schema từ `ai_engine/domain/entities.py`.

**Gọi AI Engine:** `POST /v1/consultations/analyze-transcript` (endpoint mới, §8.1).

---

### 5.2. 🔓 `suggest_icd10`

**Mục đích:** Map mô tả lâm sàng → candidate ICD-10 codes.

**Input:**
```json
{
  "clinical_text": "string",
  "max_suggestions": "integer, 1-10, default 5"
}
```

**Output:**
```json
{
  "suggestions": [
    {"code": "J06.9", "description": "...", "confidence": 0.82, "category": "respiratory"}
  ],
  "primary": { "...suggestion[0]..." }
}
```

**Gọi AI Engine:** `POST /v1/icd10/suggest` (endpoint mới, §8.2).

---

### 5.3. 🔒 `generate_soap_report`

**Mục đích:** Tool chính — sinh SOAP đầy đủ đa ngôn ngữ từ transcript.

**SHARP behavior:** Nếu `X-Patient-ID` và `X-FHIR-*` có → có thể fetch bối cảnh bệnh nhân từ FHIR và inject vào prompt. Nếu không có → vẫn chạy nhưng chỉ dựa vào transcript.

**Input:**
```json
{
  "transcript": "string",
  "output_languages": ["en", "vn", "fr", "ar"]
}
```

**Output:** Full `ClinicalReport` (SOAP 4 ngôn ngữ, medications, ICD-10, severity, urgency, next_steps) + `multilingual_summary`.

**Gọi AI Engine:** `POST /v1/consultations/soap-report` (endpoint mới, §8.3).

---

### 5.4. 🔓 `summarize_for_patient`

**Mục đích:** Lấy clinical report (JSON hoặc transcript) → bản tóm tắt ngôn ngữ thường ngày cho bệnh nhân.

**Input:**
```json
{
  "clinical_report": "dict hoặc string (JSON clinical report hoặc raw transcript)",
  "target_language": "'vn' | 'en' | 'fr' | 'ar', default 'vn'",
  "reading_level": "'simple' | 'standard', default 'simple'"
}
```

**Output:**
```json
{
  "summary": "string",
  "summary_en": "string (luôn có EN kèm theo)",
  "key_actions": ["string", "..."],
  "medications_plain": [{"name": "...", "how_to_take": "..."}],
  "follow_up": "string",
  "urgency_note": "string | null"
}
```

**Gọi AI Engine:** reuse `ClinicalAgent` với prompt khác — có thể tạo endpoint mới `POST /v1/consultations/patient-summary`.

---

### 5.5. 🔒 `process_audio_url`

**Mục đích:** Full pipeline — URL audio → SOAP report.

**Input:**
```json
{
  "audio_url": "string (URL)",
  "language_hint": "'vi'|'en'|'fr'|'ar'|'auto'",
  "async_mode": "bool, default false"
}
```

**Output (sync):** `MedicalReport` đầy đủ.
**Output (async):** `{ "session_id": "..." }` → dùng `get_consultation_status` để poll.

**Gọi AI Engine:** reuse flow của `/v1/consultations/process` nhưng nhận URL thay vì multipart upload.

**Lưu ý:** audio có thể lớn → khuyến nghị async mode mặc định cho file > 2 phút.

---

### 5.6. 🔓 `get_consultation_status`

**Mục đích:** Poll trạng thái job async.

**Input:** `{ "session_id": "string" }`

**Output:**
```json
{
  "session_id": "...",
  "status": "PENDING | PROCESSING | COMPLETED | FAILED",
  "current_step": "ScribeAgent | ClinicalAgent | ...",
  "result": "MedicalReport | null",
  "error": "string | null"
}
```

**Gọi AI Engine:** `GET /v1/consultations/{session_id}/status` (đã có).

---

### 5.7. Common error responses

Mọi tool đều phải xử lý:
- AI Engine timeout → trả `{"error": "AI engine timeout", "retry_after": 30}`
- AI Engine 5xx → trả `{"error": "...", "status_code": 500}`
- Invalid input → trả `{"error": "validation failed", "details": [...]}`
- SHARP headers thiếu khi tool yêu cầu → trả lỗi MCP với message rõ

---

## 6. SHARP-on-MCP implementation

Nguồn spec: https://sharponmcp.com/key-components.html

### 6.1. Headers

3 headers chuẩn, đọc ở request level:
- `X-FHIR-Server-URL` — base URL của FHIR server
- `X-FHIR-Access-Token` — bearer token với scope phù hợp
- `X-Patient-ID` — (optional) patient resource ID

Module `mcp_server/sharp.py`:

```python
from pydantic import BaseModel
from typing import Optional

class SharpContext(BaseModel):
    fhir_server_url: Optional[str] = None
    fhir_access_token: Optional[str] = None
    patient_id: Optional[str] = None

    @classmethod
    def from_headers(cls, headers: dict) -> "SharpContext":
        return cls(
            fhir_server_url=headers.get("X-FHIR-Server-URL"),
            fhir_access_token=headers.get("X-FHIR-Access-Token"),
            patient_id=headers.get("X-Patient-ID"),
        )

    @property
    def is_complete(self) -> bool:
        return bool(self.fhir_server_url and self.fhir_access_token)
```

### 6.2. FHIR context discovery (Prompt Opinion spec chính thức)

Nguồn: https://docs.promptopinion.ai/fhir-context/mcp-fhir-context

Trong response của `initialize` request, MCP server declare extension:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "capabilities": {
      "extensions": {
        "ai.promptopinion/fhir-context": {}
      }
    }
  }
}
```

Giá trị là **empty object** — hiện tại không có customization nào.

**LƯU Ý:** KHÔNG dùng `capabilities.experimental.fhir_context_required.value: true` — đó là spec generic SHARP, không phải spec Prompt Opinion đang dùng.

Khi user add MCP server trên trang `Configuration → MCP Servers` của Prompt Opinion:
1. User bấm "Continue" → Prompt Opinion gửi `initialize` request.
2. Prompt Opinion đọc extension declaration.
3. Nếu thấy `ai.promptopinion/fhir-context`, UI hiện thêm toggle "Trust this server with FHIR context".
4. User có thể **opt-out** — trong trường hợp đó, tool call sẽ KHÔNG kèm FHIR headers.

### 6.3. Authentication

Chọn **Anonymous access** cho MVP (không auth ở MCP level). Context qua headers là đủ cho scope hackathon. Về sau có thể thêm API key.

### 6.4. Graceful degradation khi thiếu FHIR headers

**QUAN TRỌNG:** User có thể opt-out FHIR context. Tool phải handle cả 2 case:

| Tình huống | Hành vi tool |
|---|---|
| Có đầy đủ 3 headers | Fetch patient context từ FHIR, inject vào prompt → SOAP giàu ngữ cảnh |
| Không có headers (user opt-out) | Chạy bình thường, chỉ dựa vào input của tool (vd transcript) → SOAP vẫn ra nhưng không có ngữ cảnh bệnh nhân |
| Chỉ có một vài headers (bất thường) | Log warning, chạy như case không có headers |

**KHÔNG** trả 403 khi thiếu headers. Điều đó chỉ đúng với SHARP generic spec — Prompt Opinion không yêu cầu như vậy. Nếu refuse tool call khi user opt-out, mất điểm về feasibility và UX.

Mỗi tool trong response nên có field `fhir_context_used: boolean` để minh bạch.

---

## 7. Implementation Phases

### Phase 1 — Scaffolding (nửa ngày)

- [ ] Tạo folder `mcp_server/` với `pyproject.toml`, `uv.lock`.
- [ ] Init `FastMCP` server với 1 tool dummy `ping()` trả về `"pong"`.
- [ ] Chạy được bằng `uv run python -m mcp_server.server --transport stdio`.
- [ ] Test được bằng MCP Inspector (`npx @modelcontextprotocol/inspector`).
- [ ] `.env.example` có `AI_ENGINE_BASE_URL=http://ai_engine:8000`.
- [ ] `Dockerfile` build được.

**Acceptance:** MCP Inspector kết nối được, gọi `ping` trả về đúng.

---

### Phase 2 — Transport & SHARP (nửa ngày)

- [ ] Thêm `streamable-http` transport trên port 8002.
- [ ] Implement `SharpContext.from_headers()`.
- [ ] Implement FHIR context discovery capability.
- [ ] Verify: curl `initialize` thấy `fhir_context_required=true`.
- [ ] Verify: gọi tool 🔒 mà không có header → 403.

**Acceptance:** MCP Inspector chạy được cả stdio và HTTP.

---

### Phase 3 — 2 tools "text-in" (1-1.5 ngày)

Làm trước 2 tool không cần FHIR context (đơn giản nhất):
- [ ] `analyze_transcript` + endpoint `/v1/consultations/analyze-transcript` trên AI Engine.
- [ ] `suggest_icd10` + endpoint `/v1/icd10/suggest` trên AI Engine.

- [ ] Unit test với mocked AI Engine response.
- [ ] Manual test: input transcript Tiếng Việt thật → thấy SOAP tiếng Việt ra.

**Acceptance:** 2 tool gọi được end-to-end trên MCP Inspector, pass test.

---

### Phase 4 — 4 tools còn lại (2 ngày)

- [ ] `generate_soap_report` (🔒 dùng SHARP context).
- [ ] `summarize_for_patient`.
- [ ] `process_audio_url`.
- [ ] `get_consultation_status`.
- [ ] Endpoint AI Engine tương ứng (§8).

**Acceptance:** Tất cả 6 tool pass manual test trên MCP Inspector với input thật.

---

### Phase 5 — FHIR integration light (1 ngày, nice-to-have)

- [ ] Nếu `X-FHIR-Server-URL` có, trong `generate_soap_report` fetch `Patient/{id}`, `Condition?patient={id}`, `MedicationStatement?patient={id}` từ FHIR.
- [ ] Inject tóm tắt bối cảnh bệnh nhân vào clinical prompt.
- [ ] Test với FHIR sandbox: `https://hapi.fhir.org/baseR4` hoặc SHARP sandbox `https://ts.fhir-mcp.promptopinion.ai/mcp`.

**Acceptance:** So sánh output SOAP có và không có patient context — thấy được cải thiện.

---

### Phase 6 — Deploy & Publish (1 ngày)

- [ ] Thêm service `mcp_server` vào `docker-compose.yml`.
- [ ] Deploy MCP server lên public URL (có thể host trên cùng Alibaba ECS hiện tại, hoặc Fly.io / Railway cho nhẹ).
- [ ] Đăng ký/Publish trên Prompt Opinion Marketplace — theo docs của họ sau khi tạo account.
- [ ] Smoke test: từ Prompt Opinion UI gọi được 6 tools.

**Acceptance:** Tool xuất hiện trong marketplace, agent trên Prompt Opinion gọi được.

---

### Phase 7 — Demo video (nửa ngày)

Checklist video < 3 phút (§11).

**Acceptance:** Video đã upload, submission đầy đủ trên Devpost.

---

### Rough schedule (tính từ hôm nay 18/4)

| Tuần | Việc |
|---|---|
| Tuần 1 (18–24/4) | Phase 1 + 2 + 3 |
| Tuần 2 (25/4–1/5) | Phase 4 + 5 |
| Tuần 3 (2–8/5) | Phase 6 + 7, buffer + polish |
| 9–11/5 | Submit |

Deadline cứng: **11/5 @ 23:00 EDT = 12/5 @ 10:00 giờ VN.**

---

## 8. AI Engine changes

Thêm 3 endpoint mới vào `ai_engine/api/v1/routers/consultations.py` (hoặc file mới).

### 8.1. `POST /v1/consultations/analyze-transcript`

**Request:**
```json
{ "transcript": "string", "language_hint": "..." }
```
**Response:** `MedicalReport` schema có sẵn.

**Implementation:** gọi thẳng `ClinicalAgent.analyze(transcript)`. Bỏ qua bước `ScribeAgent` vì input đã là text.

### 8.2. `POST /v1/icd10/suggest`

**Request:**
```json
{ "clinical_text": "string", "max_suggestions": 5 }
```
**Response:**
```json
{
  "suggestions": [{"code": "...", "description": "...", "confidence": 0.0, "category": "..."}],
  "primary": { ... }
}
```

**Implementation:** có thể (a) dùng `Icd10SelectorAgent` hiện có (xem `agents/icd10_selector_agent.py`) nếu nó làm được việc này, hoặc (b) wrap prompt mới của `ClinicalAgent` chỉ trả ICD-10 + confidence. Claude Code check code hiện có trước rồi quyết định.

### 8.3. `POST /v1/consultations/patient-summary`

**Request:**
```json
{
  "clinical_report": { ... } ,
  "target_language": "vn",
  "reading_level": "simple"
}
```
**Response:** schema của `summarize_for_patient` tool (§5.4).

**Implementation:** prompt mới ở tone patient-facing. Có thể tái sử dụng Qwen client nhưng với system prompt khác — tạo `patient_summary_prompts.py` song song với `clinical_prompts.py`.

### 8.4. Constraints khi sửa AI Engine

- Tuân thủ Clean Architecture (domain → application → adapters).
- Không sửa entities hiện có. Thêm mới nếu cần.
- Không sửa prompt hiện có. Thêm prompt mới.
- Giữ ruff/format clean.

---

## 9. Verification & testing

### 9.1. Commands

```bash
# Lint
cd mcp_server && uv run ruff check . && uv run ruff format --check .

# Unit tests
cd mcp_server && uv run pytest

# Manual MCP test
cd mcp_server && uv run python -m mcp_server.server --transport stdio
# → rồi mở MCP Inspector

# Integration test với AI Engine thật
docker compose up ai_engine mcp_server
# → test bằng curl hoặc MCP Inspector
```

### 9.2. Test cases tối thiểu cho từng tool

1. Happy path — input hợp lệ, mock AI Engine trả OK → assert output schema.
2. AI Engine timeout → assert error format.
3. AI Engine 500 → assert error format.
4. 🔒 tool không có SHARP header → assert 403.
5. 🔒 tool có SHARP header → assert forward đúng headers sang AI Engine.

### 9.3. Không breaking changes

Chạy test cũ của `ai_engine` + `backend` phải pass:
```bash
cd ai_engine && uv run ruff check .
cd backend && uv run ruff check .
```

---

## 10. Deployment & publication

### 10.1. docker-compose.yml — thêm service

Thêm block vào `docker-compose.yml` giữa `ai_engine` và `backend`:

```yaml
  # ── 3. MCP Server ───────────────────────────────────────────────────────────
  # Exposes vina-doctor AI capabilities as MCP tools for Prompt Opinion platform.
  # Follows SHARP-on-MCP spec for FHIR context propagation via HTTP headers.
  mcp_server:
    build:
      context: ./mcp_server
      dockerfile: Dockerfile
    image: ${MCP_SERVER_IMAGE:-ghcr.io/sotaworksvn/vina-doctor/mcp-server:latest}
    env_file:
      - .env
    environment:
      AI_ENGINE_URL: http://ai_engine:8000
      MCP_TRANSPORT: streamable-http
      MCP_HOST: 0.0.0.0
      MCP_PORT: 8002
    depends_on:
      - ai_engine
    networks:
      - app-net
    restart: unless-stopped
```

Lưu ý:
- **KHÔNG** expose `ports:` — MCP truy cập qua nginx.
- Image tag follow pattern của team: `ghcr.io/sotaworksvn/vina-doctor/mcp-server:latest`.
- Dùng `env_file: .env` giống các service khác — thêm biến MCP cần thiết vào `.env.example`.

### 10.2. nginx config — thêm location block

Sửa `nginx/nginx.conf` để route `/mcp/` đến MCP server. Streaming HTTP cần vài config đặc biệt (SSE/streamable-http):

```nginx
location /mcp/ {
    proxy_pass http://mcp_server:8002/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Forward SHARP headers to MCP server
    proxy_set_header X-FHIR-Server-URL  $http_x_fhir_server_url;
    proxy_set_header X-FHIR-Access-Token $http_x_fhir_access_token;
    proxy_set_header X-Patient-ID        $http_x_patient_id;

    # Streaming HTTP / SSE — disable buffering
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    chunked_transfer_encoding on;
}
```

**Endpoint công khai sau khi deploy:** `http://47.238.224.19/mcp/` (hoặc domain nếu team đã cấu hình).

### 10.3. GitHub Actions — cập nhật workflow

Team đã có:
- `.github/workflows/ci.yml` — lint/test
- `.github/workflows/deploy-to-ecs.yml` (hoặc tên tương tự) — build & deploy

**Cần cập nhật:**
1. `ci.yml` — thêm job `mcp-server-lint` chạy `ruff check` + `pytest` trong `mcp_server/`.
2. `deploy-to-ecs.yml` — thêm bước `docker build` và `docker push` image `ghcr.io/sotaworksvn/vina-doctor/mcp-server:latest`, thêm vào `docker compose pull && up -d` trên ECS.

Claude Code phải **đọc file workflow hiện có trước khi sửa** để giữ nguyên pattern (matrix builds, caching, service account auth, v.v.).

### 10.4. Quy tắc deploy từ AGENTS.md

Trích AGENTS.md, tuân thủ nghiêm:
- **KHÔNG** ssh vào server chạy `docker` tay.
- **KHÔNG** `git pull` / `docker build` / `docker compose up -d` trên server.
- **PHẢI** đi qua pipeline CI/CD (push → PR → merge → workflow tự deploy).
- Sau khi merge, monitor "Deploy to ECS" workflow; nếu fail → alert user.

### 10.5. Publish lên Prompt Opinion Marketplace

Sau khi MCP server đã lên ECS và `http://47.238.224.19/mcp/` truy cập được:

1. Tạo account tại promptopinion.ai.
2. Follow flow "Publish MCP Server" — cần endpoint URL, tool manifest (FastMCP tự sinh), category, tags.
3. Category: **"Medical Scribe / Clinical Documentation"**.
4. Tags: `MCP`, `SOAP`, `ICD-10`, `multilingual`, `FHIR`, `Vietnamese`.
5. Description: nhấn mạnh multilingual (Vietnamese + EN/FR/AR) và Qwen — khác biệt so với competitors.

### 10.6. 🔶 Hosting decision — HTTPS qua Google Cloud (team handle)

**Quyết định team:** MCP server deploy song song với `ai_engine/` trên hạ tầng hiện tại, HTTPS sẽ được team phụ trách DevOps setup trên **Google Cloud**. Các bước về MCP side (trong scope của Claude Code):

1. Build MCP server có route `/mcp/` qua nginx.
2. Expose port 8002 nội bộ, nginx proxy_pass sang.
3. KHÔNG cần tự config HTTPS trong MCP server — nginx/GCP load balancer handle TLS termination.
4. Khi deploy xong, endpoint cuối cùng sẽ là `https://<domain-gcp>/mcp/`.

**Handoff cho team DevOps sau khi MCP merge vào main:**
- URL public cần có HTTPS (Prompt Opinion yêu cầu).
- Nginx config trong repo đã có location `/mcp/` — DevOps chỉ cần đảm bảo TLS reach được endpoint này.
- Domain: chưa xác định, dùng IP+cert tạm cũng được nếu Prompt Opinion accept.

Trước khi vào Phase 6, xác nhận với DevOps team về timing HTTPS setup.

---

## 11. Demo video checklist (< 3 phút)

Storyline đề xuất:

1. **0:00–0:20** — Problem: bác sĩ Việt Nam viết SOAP note là gánh nặng, khám đa ngôn ngữ khó hơn.
2. **0:20–0:50** — Giới thiệu vina-doctor, chốt: lần này ta đóng gói thành MCP nên agent bất kỳ đều dùng được.
3. **0:50–1:40** — Demo trên Prompt Opinion: agent gọi `process_audio_url` với file mp3 consultation tiếng Việt → hiện transcript có diarization → hiện SOAP EN/VN/FR/AR → hiện ICD-10 + urgency.
4. **1:40–2:20** — Demo `summarize_for_patient` → ra bản bệnh nhân đọc hiểu được.
5. **2:20–2:50** — Nhấn mạnh SHARP context: gọi cùng tool với `X-Patient-ID` và thấy output có thêm bối cảnh từ FHIR.
6. **2:50–3:00** — Kêu gọi: "MCP Marketplace entry: vina-doctor."

**Props cần chuẩn bị:**
- 1 file audio consultation mẫu tiếng Việt (có sẵn trong `reference/docs/` hoặc record nhanh 1 phút).
- Prompt Opinion agent đã configure sẵn để gọi tool.
- Screen recording tool.

---

## 12. Constraints / Anti-goals

**KHÔNG làm:**
- Không sửa `backend/` hoặc `frontend/` — giữ vina-doctor production stable.
- Không đổi Qwen model, prompt hiện có của ScribeAgent / ClinicalAgent.
- **Không đụng vào `mr_cuong_ai_engine/` từ MCP side** — đây là R&D sandbox của Cường chứa prompts thế hệ mới, không phải target của MCP proxy. Khi Cường hoàn thiện prompts ở đó, team sẽ merge vào `ai_engine/agents/*_prompts.py`. MCP không phụ thuộc.
- Không thêm dependency nặng (pytorch, transformers, v.v.) — MCP server phải nhẹ.
- Không commit `.env` thật vào repo.
- Không viết tool có khả năng ghi data PII nhạy cảm ra log mà không redact.
- Không skip FastMCP's validation — để schema của tool rõ cho LLM client.
- Không hard-code FHIR server URL — luôn lấy từ `X-FHIR-Server-URL` header.
- Không ssh vào ECS chạy docker tay (AGENTS.md nghiêm cấm).

**Clean Architecture vẫn áp dụng:**
- `mcp_server/tools/` = adapter layer.
- Business logic (nếu có, rất ít) để trong module riêng.
- Tools KHÔNG import trực tiếp httpx — dùng qua `ai_engine_client.py`.

**Python quirk (AGENTS.md):**
- Không tạo `src/` layout trong `mcp_server/` — sẽ phá import path.
- `pyproject.toml` dùng `package-dir = {"" = ".."}` giống các service khác.

---

## 13. Open Questions cần người dùng confirm

Trước khi giao cho Claude Code, xin bạn xác nhận:

1. **Architecture option A (HTTP proxy) hay B (in-process)?** — đề xuất A.
2. **Stack Python + FastMCP** — ok?
3. **Hosting MCP server:** Alibaba ECS cùng với hệ hiện tại / Fly.io / khác?
4. **FHIR integration:** làm Phase 5 ngay hay chỉ stub (echo context) nếu chạy đua thời gian?
5. **Audio URL source** cho `process_audio_url`: chấp nhận URL public bất kỳ, hay chỉ signed URL từ domain cụ thể (security)?
6. **Demo video language:** tiếng Việt phụ đề Anh, hay tiếng Anh hoàn toàn?
7. **Submit individual hay team?** — nếu team cần khai báo thành viên.
8. **Có muốn thêm tool thứ 7 `fetch_patient_fhir_context`** (đọc Patient + Condition + MedicationStatement từ FHIR) như standalone tool không? — sẽ mạnh cho demo.

---

## 14. Hand-off cho Claude Code

Khi Claude Code nhận việc, context cần cung cấp:

1. File này (`BUILDING_INSTRUCTION.md`).
2. Quyền đọc toàn bộ repo hiện tại để hiểu cấu trúc.
3. File `AGENTS.md` ở repo root (đã có trong repo) — chứa rules như Clean Architecture, SOLID, uv, git workflow, Deploy to ECS workflow.
4. Các file trong `.github/instructions/` — clean-architecture, solid-principles, agent-engineering.
5. Confirm đã đọc §3 (architecture), §5 (tool spec), §6 (SHARP), §8 (AI engine changes), §15 (team coord).
6. Bắt đầu Phase 1, PR nhỏ mỗi phase, không gộp.

Prompt cho Claude Code khi mở session:

> "Đọc `BUILDING_INSTRUCTION.md`, `AGENTS.md`, và `.github/instructions/*`. Xác nhận hiểu Phase 1 và §15. Chạy `ls mcp_server/` trước — nếu chưa có thì tạo. Bắt đầu Phase 1. Khi xong mở PR `feature/mcp-phase-1-scaffold` rồi dừng chờ review."

---

## 15. Team coordination & git workflow

> Repo có 193 commits, 2 PRs đang mở, team đang active — MCP work phải khéo để không dẫm chân người khác.

### 15.1. Tạo branch theo convention của team

Theo AGENTS.md, dùng `git` CLI bình thường (không phải GitButler trừ khi đang trên `gitbutler/workspace`):

```bash
# Branch naming convention: feature/mcp-<phase>-<desc>
git checkout -b feature/mcp-phase-1-scaffold
git checkout -b feature/mcp-phase-2-sharp
git checkout -b feature/mcp-phase-3-text-tools
git checkout -b feature/mcp-phase-4-remaining-tools
git checkout -b feature/mcp-phase-5-fhir-integration
git checkout -b feature/mcp-phase-6-deploy-publish
```

Mỗi phase = 1 branch = 1 PR riêng. Không gộp nhiều phase vào 1 PR (dễ conflict, khó review).

### 15.2. PR workflow (trích AGENTS.md)

```bash
# Push + tạo PR
gh pr create \
  --title "feat(mcp): phase 1 — MCP server scaffold" \
  --body "<description>" \
  --base main \
  --head feature/mcp-phase-1-scaffold \
  --repo sotaworksvn/vina-doctor

# Sau khi CI pass, auto-merge
gh pr merge <pr-number> --merge --auto --delete-branch --repo sotaworksvn/vina-doctor
```

**LƯU Ý:** AGENTS.md yêu cầu "always wait for CI to pass then merge automatically". Claude Code phải tuân thủ.

### 15.3. Tránh conflict với team

Các khu vực **có rủi ro conflict**:

| Khu vực | Rủi ro | Mitigation |
|---|---|---|
| `docker-compose.yml` | Cao — team có thể đang sửa | Pull main trước khi sửa, PR nhỏ, merge nhanh |
| `.github/workflows/deploy-to-ecs.yml` | Cao — deploy pipeline | Đọc kỹ workflow hiện có trước khi sửa |
| `nginx/nginx.conf` | Trung bình | Chỉ thêm location block, không sửa khác |
| `.env.example` | Thấp | Chỉ thêm biến MCP_*, không đụng biến khác |
| `ai_engine/` | Trung bình | Chỉ thêm endpoint mới, không sửa agent hiện có |
| `mr_cuong_ai_engine/` | 🚫 | KHÔNG ĐỤNG |

### 15.4. PRs hiện đang mở

Có 2 PR đang mở trên repo. Trước khi bắt đầu, Claude Code nên:
1. `gh pr list --repo sotaworksvn/vina-doctor` để xem 2 PR đó đang làm gì.
2. Nếu PR đó sửa `ai_engine/` hoặc `docker-compose.yml`, **chờ merge trước** khi start Phase 2 trở đi.

### 15.5. Spec-driven development (`.specify/`)

Repo có folder `.specify/` cho thấy team đang dùng spec-driven workflow (có lẽ GitHub Spec Kit). Trước mỗi phase lớn:
1. Xem có spec nào trong `.specify/` liên quan đến MCP không — nếu có, follow.
2. Cân nhắc viết 1 spec file mới `/specs/mcp-server.md` trước khi code (hoặc check xem team có workflow nào cụ thể).

### 15.6. Commit message convention

Theo team style (suy đoán từ AGENTS.md):
```
feat(mcp): add analyze_transcript tool
fix(mcp): handle AI engine timeout
chore(mcp): upgrade mcp sdk to 1.3.1
docs(mcp): add SHARP context guide
```

---

*Document version 3 — 19 April 2026. Updated after reading real repo (new zip), Prompt Opinion official docs (docs.promptopinion.ai), and confirming ai_engine vs mr_cuong_ai_engine decision. Please review and flag edits before handoff.*
