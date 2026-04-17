# GovDoc SecureFlow — Multi-Pass Implementation Plan

Version: 1.1.1  
Status: Implementation handoff note  
Primary input: `govdoc_source_of_truth_plan_v1_1.md`  
Scope: turn the existing Google AI Studio baseline (real frontend + backend, mocked business logic) into a real, testable MVP with Alibaba Model Studio integration, demo mode, and deterministic QA/deployment paths.

Changelog since 1.1:
- Corrected §3.1 runtime to Python 3.12 (matches the repo Dockerfile `python:3.12-alpine`).
- Rewrote §5.1 `make check-credentials` to defer to the locked 5-model probe contract in §17.7 (removed "optional qwen-max" language).
- Added §3.4 Workflow-state ↔ `document.status` mapping.
- Expanded §15 item 11 to list `make check-credentials`, `make test-ai`, and `make test-e2e` alongside the other required targets.
- Resolved `prompt_version` primary-key ambiguity: composite PK `(id, stage)` where `id` is the SHA-256[:12] of the prompt file bytes (§17.10, Pass 1 entity schema).
- Pinned `POST /documents/{id}/analyze` idempotency: if an `ai_analysis` row already exists for the `(document_id, active prompt_version)` pair, return it without calling the model (§Pass 6 endpoint inventory).
- Normalized all `config/models.yaml` / `config/prompt_versions.yaml` references to `api/config/...` (§6.1 note, §17.2, §17.10).

Changelog since 1.0:
- Locked the stack (§3.1), role simulation contract (§3.2), and synchronous pipeline model (§3.3).
- Dropped `MODEL_*` env vars; models live only in `api/config/models.yaml`. Added `MODELSTUDIO_DASHSCOPE_URL`, `MODELS_CONFIG_PATH`, `ROLES_CONFIG_PATH`, `CACHED_AI_STORAGE_ROOT` (§6.1).
- Added entity field schema (Pass 1) and API endpoint inventory (Pass 6).
- Clarified `extraction_method` values (§17.4), locked credential-check return keys (§17.7), split integration marker into `mock_integration` / `live_integration` (§17.9).
- Added prompt versioning scheme (§17.10), cached AI storage layout (§17.11), fence-stripping helper contract (§17.12).
- Added `make test-ai` and `make test-e2e` intent blocks (§5.1).

---

## 1) Goal

Implement the GovDoc SecureFlow MVP defined by the source-of-truth plan, preserving:

- selected use-case: incoming administrative document intake + triage
- no real login; role simulation only
- end-to-end workflow:
  `intake → registration → distribution → review → consultation → response`
- Alibaba Model Studio as the AI backend
- fail-fast behavior
- no hidden errors / no fake fallback logic
- docker-compose deployment
- Makefile-driven developer workflow
- local and remote deployment flows
- later-ready hooks for AI quality evaluation and demo mode

This note is **implementation-only**. Verification details belong in the paired test plan.

---

## 2) Non-negotiable engineering rules

1. **Fail fast**
   - Missing config, malformed config, bad API responses, schema mismatch, unsupported file type, and invalid workflow transition must return explicit errors.
   - Never silently downgrade behavior.

2. **No hidden errors**
   - Do not swallow Model Studio errors and replace them with fake/demo outputs in normal mode.
   - Demo mode may use cached seed outputs only when explicitly enabled and visibly labeled.

3. **No fake success state**
   - Never mark a document as analyzed/routed if the AI call failed.
   - Never mark deployment as successful if health checks failed.

4. **No stack rewrite**
   - Use the baseline repo structure and stack already generated.
   - Refactor only as needed to make the app maintainable and testable.

5. **Deterministic guards around AI**
   - AI may recommend.
   - Application logic owns state mutation, persistence, permissions, and workflow transitions.

6. **Every pass must leave the repo deployable**
   - `make build`
   - `make test`
   - `make up`
   must remain valid or fail with a clear actionable reason.

---

## 3) Starting assumptions

This plan assumes the baseline repo already contains:

- real frontend
- real backend API
- mocked core/business logic
- seed/demo records
- basic scenes aligned with the source-of-truth doc
- docker-based local development possible or at least scaffolded

If the baseline diverges materially from the source-of-truth structure, fix the structure first instead of layering new logic on top of wrong entities.

### 3.1 Committed stack

The stack is fixed for this phase. Do not introduce alternatives.

**Backend (`api/`)**
- Python 3.12 (matches `deploy/api.Dockerfile` base image)
- FastAPI (ASGI via uvicorn)
- SQLAlchemy 2.x + Alembic (migrations)
- SQLite, single file at `data/govdoc.db` (WAL mode)
- Pydantic v2 (request/response + AI schemas)
- `openai` SDK (for OpenAI-compatible endpoints)
- `httpx` (for DashScope rerank endpoint)
- `pypdf` (born-digital extraction)
- `pdf2image` + `poppler-utils` (scan render)
- `pytest` + `pytest-asyncio`

**Frontend (`web/`)**
- React 19
- Vite 6
- React Router v7
- TypeScript
- Playwright (E2E)

**Shared**
- docker-compose (web + api + optional reverse proxy)
- Make (developer entrypoint)

### 3.2 Role simulation contract

- No auth, no sessions, no tokens.
- Every protected API request must carry header `X-GovDoc-Role: <role_id>`.
- Allowed role ids are seeded and loaded from `config/roles.yaml`.
- FastAPI dependency resolves the header into a `CurrentRole` object used by every route.
- Missing header on a protected route → `400 MISSING_ROLE_HEADER`.
- Unknown role id → `403 UNKNOWN_ROLE`.
- Role is the only identity input; no per-user records in MVP.
- Audit events record the role id verbatim.

### 3.3 Pipeline execution model

- AI analysis is **synchronous** for MVP.
- Upload flow: `POST /documents` persists the raw file and `document` row, then (in the same request) runs deterministic extraction and the AI analysis pipeline, then returns the created `document` + `ai_analysis` payload.
- On any pipeline failure, the request returns non-2xx with an explicit error class and the document is marked `status="ingest_failed"`; no partial success is reported as success.
- Re-analysis is triggered by explicit `POST /documents/{id}/analyze` (idempotent per prompt version — see Pass 6 endpoint inventory).
- No background worker, no task queue, no Celery/RQ in this phase.

### 3.4 Workflow-state ↔ `document.status` mapping

The source-of-truth workflow (`intake → registration → distribution → review → consultation → response`) maps to the `document.status` enum in §Pass 1 entity schema as follows. The workflow label is the user-facing stage; the status is the persisted value used by the state machine and audit log.

| Workflow stage | `document.status` | Entered by |
|---|---|---|
| intake (just uploaded) | `received` | `POST /documents` success (before extraction) |
| extraction done | `extracted` | deterministic extractor completes |
| AI analysis done | `analyzed` | `POST /documents` / `POST /documents/{id}/analyze` success |
| registration / distribution | `routed` | `POST /documents/{id}/approve-routing` or `.../reroute` |
| review | `under_review` | reviewer opens record (implicit on read by reviewer role) or explicit claim action |
| consultation | `in_consultation` | `POST /documents/{id}/request-consultation` |
| response / closeout | `approved` then `closed` | `POST /documents/{id}/close` (via approved) |
| out-of-scope branch | `out_of_scope` | `POST /documents/{id}/mark-out-of-scope` |
| intake pipeline error | `ingest_failed` | extraction or storage failure in `POST /documents` |
| analysis pipeline error | `analysis_failed` | AI adapter raises after extraction succeeded |

Transitions not listed above are invalid and must be rejected with `INVALID_TRANSITION`. The state machine is the single source of truth for allowed moves; UI must not perform implicit transitions client-side.

---

## 4) Required deliverables

By the end of this implementation plan, the repo must include:

- real business workflow implementation
- real deterministic extraction path for born-digital docs
- real Model Studio integration
- real Qwen-OCR path for scan scenarios
- real routing/review/consultation state changes
- real retrieval/evidence panel backend
- demo mode with seeded scenarios and optional cached AI outputs
- clear Makefile workflow
- docker-compose deployment
- remote deployment flow via `make up-remote`
- health checks
- unit tests
- integration tests
- API contract tests
- Playwright-ready UI/E2E hooks
- AI quality evaluation hooks and scripts

---

## 5) Required Makefile targets

The repo must include at minimum:

- `make lint`
- `make build`
- `make test`
- `make ci`
- `make check-credentials`
- `make up`
- `make down`
- `make logs`
- `make test-ai`
- `make test-e2e`
- `make qa`
- `make up-remote`

### 5.1 Target intent

#### `make lint`
Run all static quality checks for the chosen stack.

#### `make build`
Build frontend, backend, and Docker artifacts.

#### `make test`
Run non-live automated tests:
- unit
- contract
- deterministic integration
- no external Model Studio dependency

#### `make ci`
Run:
- lint
- build
- test

Fail immediately on first failing stage.

#### `make check-credentials`
Explicitly validate Model Studio credentials and required model availability by running the locked 5-model live probe defined in §17.7. All five probes (`classify`, `escalate`, `embed`, `ocr`, `rerank`) are mandatory; none are optional. Returns non-zero if any probe fails or if any required env var is missing.

#### `make up`
Run docker-compose locally and block on health checks.

#### `make qa`
Run local API/UI smoke checks after `make up`.

#### `make test-ai`
Run live AI quality evaluation against the bundled data pack. Invokes pytest with `--live --integration` and produces `data/ai_quality_report.json` + a human-readable markdown summary. Requires valid Model Studio credentials. Exits non-zero on hard-fail thresholds (see test plan §7.5).

#### `make test-e2e`
Run the Playwright suite (`web/tests-e2e/`) against the running local docker-compose stack. Requires `make up` to have completed successfully. Fails fast if the stack is not reachable.

#### `make up-remote`
Build images locally, export them, transfer them to remote host with `rsync`, load them on remote host, deploy with docker compose, and run remote health checks.

---

## 6) Environment and configuration contract

The implementation must standardize configuration in a single documented contract.

### 6.1 Required environment variables

At minimum:

- `APP_ENV`
- `APP_PORT`
- `WEB_PORT`
- `API_BASE_URL`
- `MODELSTUDIO_API_KEY`
- `MODELSTUDIO_BASE_URL` (OpenAI-compatible endpoint)
- `MODELSTUDIO_DASHSCOPE_URL` (DashScope endpoint, used by rerank)
- `MODELS_CONFIG_PATH` (defaults to `api/config/models.yaml`)
- `ROLES_CONFIG_PATH` (defaults to `api/config/roles.yaml`)
- `ENABLE_DEMO_MODE`
- `ENABLE_CACHED_AI_RESULTS`
- `ENABLE_LIVE_OCR`
- `ENABLE_LIVE_EMBEDDINGS`
- `LOCAL_FILE_STORAGE_ROOT`
- `PROMPT_CONFIG_PATH`
- `CACHED_AI_STORAGE_ROOT` (defaults to `data/cached_ai`)
- `REMOTE_HOST`
- `REMOTE_USER`
- `REMOTE_APP_DIR`

**Model names are not env vars.** All model ids live in `api/config/models.yaml` (see §17.2/§17.6). This keeps the model → role mapping in one place and prevents env drift.

### 6.2 Fail-fast configuration rules

- Startup must fail if any required variable is missing.
- `make check-credentials` must fail if the API key is invalid, base URL is wrong, or required models are unavailable.
- If demo mode is on, the API must still clearly indicate whether a response was live or cached.

---

## 7) Suggested repository responsibilities

The exact folder names may follow the baseline stack, but responsibilities must map cleanly to:

- `web/`
- `api/`
- `shared/` or equivalent shared schema layer
- `config/`
- `prompts/`
- `data/` or demo fixtures
- `scripts/`
- `tests/`
- `deploy/`

The critical requirement is separation between:
- UI
- deterministic business logic
- AI adapter logic
- storage
- workflow state
- test fixtures

---

## 8) Multi-pass implementation plan

---

## Pass 0 — Baseline audit and repo hardening

### Objective
Turn the Google AI Studio baseline into a stable starting point without changing the intended product shape.

### Tasks
- audit frontend screens against source-of-truth scenes
- audit backend entities against source-of-truth entities
- remove fake shortcuts that contradict the target workflow
- add strict config loader
- add health endpoints for web/api
- add baseline Makefile and docker-compose scaffolding if missing
- ensure local boot path is deterministic
- document current gaps explicitly in repo notes

### Must-have outputs
- working local boot path
- repo can lint/build/test in scaffold form
- wrong baseline entities corrected before real implementation begins
- all mocks are visibly isolated and tagged

### Acceptance criteria
- `make lint`, `make build`, and `make test` exist and run
- `make up` starts web + api through docker-compose
- health endpoint returns explicit healthy/unhealthy state
- no baseline path hides errors behind generic “success” UI
- all remaining mock paths are discoverable and labeled

---

## Pass 1 — Domain model, workflow engine, and persistence

### Objective
Implement the real domain model and workflow state machine.

### Tasks
- define/normalize entities:
  - document
  - document_file
  - extracted_artifact
  - ai_analysis
  - routing_decision
  - consultation_note
  - audit_event
  - role
  - department
  - prompt_version
  - demo_scenario
- implement workflow states from source-of-truth
- implement deterministic transition guards
- implement audit-event writing on every state mutation
- implement role simulation policy enforcement on backend
- implement security-level storage and visibility flags
- implement seed loader for bundled data pack metadata

### Must-have outputs
- stable persistence model
- state machine with explicit invalid-transition errors
- role-based action restrictions enforced in backend

### Acceptance criteria
- invalid workflow transitions return explicit non-2xx errors
- every mutation writes an audit event
- role switcher changes allowed actions and view shape
- no direct frontend-only permissions; backend validates too
- seed scenarios load cleanly from fixtures

### Entity field schema

All entities use UUID string primary keys (`id`) and timestamptz `created_at` / `updated_at` unless noted. Field types are SQLAlchemy-flavored.

**document**
- `id: str (UUID)`
- `title: str`
- `doc_number: str | None`
- `issuing_agency: str | None`
- `received_at: datetime`
- `status: enum(received, extracted, analyzed, routed, under_review, in_consultation, approved, closed, out_of_scope, ingest_failed, analysis_failed)`
- `security_level: enum(unclassified, confidential, secret, top_secret)`
- `urgency: enum(normal, urgent, critical)`
- `assigned_department_id: str | None → department.id`
- `assigned_reviewer_role: str | None`
- `current_prompt_version: str | None`
- `notes: text | None`

**document_file**
- `id, document_id → document.id`
- `storage_key: str` (path under `LOCAL_FILE_STORAGE_ROOT`)
- `original_filename: str`
- `mime_type: str`
- `size_bytes: int`
- `sha256: str`
- `is_primary: bool`

**extracted_artifact**
- `id, document_id → document.id`
- `extraction_method: enum(pypdf, render_ocr, qwen-ocr, docx, plaintext)`
- `text: text`
- `page_count: int`
- `warnings: json (list[str])`
- `extracted_at: datetime`

**ai_analysis**
- `id, document_id → document.id`
- `stage: enum(classify, summarize, route, escalate)`
- `model_name: str`
- `prompt_version: str` (see §17.10)
- `source: enum(live, cached)`
- `payload_json: json` (validated pydantic dump)
- `confidence: float | None`
- `created_at: datetime`

**routing_decision**
- `id, document_id`
- `suggested_department_id: str | None`
- `final_department_id: str | None`
- `decided_by_role: str | None`
- `decision: enum(accepted, rerouted, escalated, out_of_scope)`
- `rationale: text | None`

**consultation_note**
- `id, document_id`
- `author_role: str`
- `target_role: str | None`
- `body: text`
- `resolved_at: datetime | None`

**audit_event**
- `id, document_id | None`
- `actor_role: str | None`
- `event_type: str` (e.g. `document.created`, `workflow.transition`, `ai.call`, `ai.rejected`)
- `from_state: str | None`
- `to_state: str | None`
- `metadata_json: json`
- `occurred_at: datetime`

**role** (seeded, read-only at runtime)
- `id: str` (e.g. `intake_clerk`, `reviewer`, `supervisor`)
- `label: str`
- `allowed_actions: json (list[str])`

**department** (seeded)
- `id: str`
- `name: str`
- `description: str | None`

**prompt_version** (registry, composite primary key `(id, stage)`)
- `id: str` — first 12 hex chars of SHA-256 of prompt file bytes (see §17.10)
- `stage: enum(classify, summarize, route, escalate)`
- `file_path: str`
- `label: str | None`
- `registered_at: datetime`

The composite key exists because two stages could theoretically share identical file bytes (hash collision in content), and we want stage-scoped uniqueness. In practice this is rare, but it lets `ai_analysis.prompt_version` + `ai_analysis.stage` unambiguously identify the prompt used.

**demo_scenario** (seeded)
- `id: str`
- `name: str`
- `description: str`
- `document_id: str → document.id`
- `category: enum(hero, ambiguity, scan, out_of_scope)`

---

## Pass 2 — File intake, storage, and deterministic extraction

### Objective
Implement real intake and extraction for born-digital files.

### Tasks
- implement file validation:
  - allowed types
  - size constraints
  - empty/corrupt-file rejection
- implement local file storage adapter for MVP/demo
- persist raw original file path/key separately from extracted outputs
- implement deterministic text extraction for born-digital PDF/DOCX
- implement extraction warnings and metadata
- implement normalized artifact schema
- wire intake queue UI to real backend records

### Must-have outputs
- uploaded document creates persistent record
- raw file retained
- normalized artifact persisted separately
- extraction method tagged per file

### Acceptance criteria
- uploading supported files creates document + document_file + extracted_artifact
- corrupt/unsupported files fail with clear error
- born-digital extraction is reproducible and inspectable
- record detail page shows raw preview info and extracted text preview
- no AI call is triggered before deterministic extraction completes or fails clearly

---

## Pass 3 — Alibaba credential validation and Model Studio adapter layer

### Objective
Implement the real Model Studio adapter and explicit credential checks.

### Tasks
- add Model Studio client wrapper
- add strict typed request/response models
- implement:
  - generation call wrapper
  - OCR call wrapper
  - embedding call wrapper
  - rerank wrapper
- implement error normalization:
  - auth errors
  - schema errors
  - rate-limit errors
  - unavailable model errors
- implement `make check-credentials`
- create small bundled credential-check fixtures
- store model/prompt metadata with every live AI result

### Must-have outputs
- one adapter layer only
- no AI calls directly from controllers/components
- explicit credential validation path

### Acceptance criteria
- invalid API key fails fast and visibly
- wrong base URL fails fast and visibly
- unavailable model names fail fast and visibly
- `make check-credentials` exits non-zero on any failing dependency
- every successful live AI call records model name + prompt version + timestamp

---

## Pass 4 — Core AI analysis pipeline

### Objective
Replace mocked classification/summarization/routing with real Qwen-backed logic.

### Tasks
- implement classification prompt family
- implement summary prompt family
- implement routing prompt family
- define strict structured output schema
- implement parse/validate/reject flow for malformed AI output
- persist AI analysis separately from workflow state
- implement confidence threshold handling
- implement escalation to `qwen-max` for ambiguous cases
- surface `needs_human_review`, `needs_consultation`, `needs_supervisor_review`
- connect analysis results to record detail page

### Must-have outputs
- one real analysis pipeline
- no free-form AI response used directly as state
- escalation path for ambiguous documents

### Acceptance criteria
- analysis pipeline returns structured JSON only
- malformed AI output is rejected with explicit error and audit trace
- ambiguous-case logic triggers escalation instead of pretending certainty
- record detail page shows:
  - type
  - summary
  - routing suggestion
  - confidence
  - rationale
- no hidden fallback when live analysis fails

---

## Pass 5 — OCR fallback, scan path, and hard-case handling

### Objective
Implement the scan path and hard-case logic needed for demo robustness.

### Tasks
- implement scan detection heuristics
- implement Qwen-OCR flow for scan-like inputs
- persist OCR extraction method and warnings
- add out-of-scope classification handling
- add hard-case flags:
  - low_quality_scan
  - multi_department
  - out_of_scope
- show OCR path in UI and audit log
- implement “mark as out-of-scope” review action

### Must-have outputs
- scan demo path is real
- OCR usage is visible
- out-of-scope cases are handled honestly

### Acceptance criteria
- derived low-quality scan fixtures go through OCR path
- OCR failures surface explicit errors and do not fake successful analysis
- out-of-scope documents can be reviewed and labeled as such
- scan-vs-born-digital extraction method is visible in record detail
- hard-case flags can be seeded and displayed

---

## Pass 6 — Review, routing approval, consultation, and closeout

### Objective
Implement the human-in-the-loop workflow beyond AI analysis.

### Tasks
- implement review actions:
  - approve
  - change category
  - reroute
  - request consultation
  - escalate
  - mark out-of-scope
- implement consultation thread model and API
- implement supervisor visibility path
- implement response/disposition state
- implement tracking dashboard state timeline
- implement role-filtered data visibility
- persist every action to audit log

### Must-have outputs
- real human review path
- real consultation path
- real end-to-end workflow progression

### Acceptance criteria
- hero flow can move from intake to closeout through backend state changes
- consultation requests and responses persist correctly
- supervisor role sees different summary/dashboard state than clerk
- unauthorized role actions fail explicitly
- timeline view reflects real recorded workflow states

### API endpoint inventory (minimum)

All protected endpoints require `X-GovDoc-Role`. Responses are JSON; errors are `{ "error": { "code": str, "message": str, "details": {...} } }`.

**Health / meta**
- `GET /healthz` — liveness, no role required
- `GET /readyz` — readiness (db reachable, config loaded), no role required
- `GET /meta/roles` — list seeded roles
- `GET /meta/departments` — list seeded departments
- `GET /meta/prompt-versions` — list registered prompt versions

**Documents**
- `POST /documents` — multipart upload; runs extraction + analysis synchronously; returns `{document, extracted_artifact, ai_analysis[]}`
- `GET /documents` — list with filters (`status`, `department`, `q`, `scenario`)
- `GET /documents/{id}` — full record (document + files + artifact + analysis + routing + consultation + audit)
- `GET /documents/{id}/file` — raw file stream
- `POST /documents/{id}/analyze` — re-run analysis (supervisor only). **Idempotency rule:** if an `ai_analysis` row already exists for this `document_id` at the currently-active `prompt_version` (for each relevant stage), return the existing rows without calling the model. Only stages whose prompt hash differs from the recorded one are re-run. A `force=true` query param bypasses the cache and always calls the model, writing a new `ai_analysis` row (old rows are retained).

**Workflow actions**
- `POST /documents/{id}/approve-routing` — reviewer/supervisor
- `POST /documents/{id}/reroute` — body `{department_id, rationale}`
- `POST /documents/{id}/request-consultation` — body `{target_role, body}`
- `POST /documents/{id}/resolve-consultation/{note_id}`
- `POST /documents/{id}/escalate` — supervisor only
- `POST /documents/{id}/mark-out-of-scope`
- `POST /documents/{id}/close`

**Evidence / retrieval**
- `GET /documents/{id}/evidence` — ranked reference chunks (Pass 7)
- `POST /retrieval/search` — body `{query, top_k}` (Pass 7, debug-friendly)

**Demo**
- `GET /demo/scenarios` — list seeded scenarios
- `POST /demo/reset` — reset demo data (dev/demo env only; fails in prod)

**Error codes (minimum set)**
`MISSING_ROLE_HEADER`, `UNKNOWN_ROLE`, `FORBIDDEN_ACTION`, `INVALID_TRANSITION`, `UNSUPPORTED_MIME`, `CORRUPT_FILE`, `EXTRACTION_FAILED`, `OCR_FAILED`, `AI_AUTH_FAILED`, `AI_MODEL_UNAVAILABLE`, `AI_SCHEMA_INVALID`, `AI_RATE_LIMITED`, `PERSISTENCE_FAILED`, `NOT_FOUND`.

---

## Pass 7 — Retrieval, reference corpus, prompt versioning, and demo mode

### Objective
Implement the evidence panel and stable demo mode.

### Tasks
- ingest selected reference corpus
- chunk normalized reference text
- embed reference chunks
- implement retrieval endpoint
- implement reranking
- show evidence panel in UI
- implement prompt version registry
- implement demo scenarios with optional cached AI outputs
- clearly label cached vs live analysis results

### Must-have outputs
- retrieval-backed evidence panel
- demo mode safe for live presentation
- prompt/version traceability

### Acceptance criteria
- evidence panel shows ranked references for analyzed docs
- prompt version used in each AI result is inspectable
- demo mode can replay hero scenario without unstable hidden behavior
- cached results are visibly marked and not confused with live mode
- retrieval can be disabled/enabled without breaking core workflow

---

## Pass 8 — Deployment, remote deployment, and production-like QA hooks

### Objective
Make the app easy to run locally and remotely with one repeatable release path.

### Tasks
- finalize docker-compose for web + api
- ensure health checks and dependency ordering
- implement `make up`
- implement `make qa`
- implement `make up-remote`:
  1. run local preflight
  2. run `make ci`
  3. build Docker images
  4. save images to tar files
  5. compress release bundle
  6. `rsync` bundle to remote host
  7. load images on remote host
  8. run remote docker compose deploy
  9. run remote health checks
  10. print explicit success/failure logs
- ensure remote deploy does not assume any Alibaba-specific service beyond “plain VPS host”

### Must-have outputs
- local deploy path
- remote deploy path
- post-deploy QA entrypoint

### Acceptance criteria
- `make up` starts a working local stack
- `make qa` verifies local API + UI smoke checks
- `make up-remote` fails fast if remote vars are missing
- `make up-remote` fails fast if rsync, image load, compose up, or health checks fail
- successful remote deployment leaves the app reachable and healthy

---

## 9) Remote deployment contract (`make up-remote`)

`make up-remote` must do exactly this:

1. validate required variables:
   - `REMOTE_HOST`
   - `REMOTE_USER`
   - `REMOTE_APP_DIR`
2. validate Docker + rsync availability locally
3. run `make ci`
4. build release images
5. export images as `.tar`
6. compress release payload
7. upload payload via `rsync`
8. run remote shell commands:
   - create target dir if missing
   - unpack payload
   - load Docker images
   - run docker compose up
   - run remote health checks
9. return success only if remote health checks pass

### Rules
- do not SSH and mutate random host paths outside configured app dir
- do not rely on pulling fresh code on the remote host
- deployment must be artifact-driven
- remote deploy logs must be stored or printed clearly

---

## 10) Error-handling requirements

The implementation must explicitly surface these classes of errors:

- invalid/missing env vars
- invalid file upload
- unsupported mime type
- corrupt file
- deterministic extraction failure
- OCR failure
- Model Studio auth failure
- unavailable model
- malformed AI output
- persistence failure
- invalid workflow transition
- unauthorized role action
- retrieval indexing failure
- deployment failure
- remote health-check failure

### UI requirement
The UI may be user-friendly, but it must not hide that a real error occurred.
There must be enough detail in logs/API payloads for debugging.

---

## 11) Logging and auditability requirements

Implement structured logging for:

- request id
- document id
- role
- workflow transition
- AI call start/end
- model name
- prompt version
- cached/live source
- error class
- deployment stage

Audit events must be separate from generic logs.

---

## 12) Required scripts/helpers

The repo should include scripts for:

- seed demo records
- seed reference corpus
- generate cached AI results
- run credential check
- run local QA
- run remote deploy
- reset local demo data
- export AI quality fixtures

---

## 13) Required demo scenarios to preserve during implementation

Implementation must preserve these seeded scenarios:

1. **Hero scenario**
   - normal incoming document
   - clear route
   - human approval
   - consultation
   - closeout

2. **Ambiguity scenario**
   - multiple plausible departments
   - escalation or consultation suggestion

3. **Scan scenario**
   - low-quality scan
   - OCR path visible

4. **Out-of-scope scenario**
   - document should not be forced into fake in-scope certainty

---

## 14) Pass-by-pass acceptance summary

### Pass 0
Repo stable and baseline gaps corrected.

### Pass 1
Domain/workflow core is real.

### Pass 2
Intake/storage/extraction core is real.

### Pass 3
Credential checks and AI adapter are real.

### Pass 4
Classification/summary/routing are real.

### Pass 5
OCR + hard-case handling are real.

### Pass 6
Human review and workflow progression are real.

### Pass 7
Evidence panel + demo mode are real.

### Pass 8
Local and remote deploy paths are real.

---

## 15) Overall acceptance criteria

The implementation is complete only when all of the following are true:

1. the app supports the selected target use-case end-to-end
2. there is no real-login dependency
3. role simulation is enforced in backend and visible in UI
4. raw files and normalized artifacts are both preserved
5. `make check-credentials` verifies Model Studio connectivity and required models
6. live AI calls use Model Studio through one adapter layer only
7. malformed AI outputs are rejected, not silently accepted
8. OCR path works for seeded scan scenarios
9. review/consultation/closeout workflow is real
10. evidence panel is real enough to support demo credibility
11. `make lint`, `make build`, `make test`, `make ci`, `make up`, `make qa`, `make check-credentials`, `make test-ai`, `make test-e2e`, and `make up-remote` all exist and behave deterministically (CI-safe targets never require live credentials; live targets fail fast if credentials are missing)
12. local and remote deployment fail fast on missing config or bad health state
13. no hidden-error or fake-success behavior remains in normal mode
14. the repo is ready for paired verification through the dedicated test plan

---

## 16) Explicit non-goals for coding agents

Do not spend time on:
- real auth
- Alibaba OSS migration for this phase
- cross-province integrations
- production RBAC admin UI
- full legal-research assistant behavior
- fancy prompt playgrounds
- generic agent frameworks
- cosmetic refactors unrelated to target functionality

If a proposed change does not materially improve:
- workflow correctness
- AI correctness
- testability
- deployability
- demo reliability

then do not do it in this phase.

---

## 17) Model Studio integration reference

This section is concrete and prescriptive. All AI adapter code in `api/` must follow these patterns exactly, derived from the validated `alibaba-api-test` reference repo.

---

### 17.1 Environment variables required

| Variable | Purpose |
|---|---|
| `MODELSTUDIO_API_KEY` | Bearer token for both endpoints |
| `MODELSTUDIO_BASE_URL` | OpenAI-compatible base URL (chat, embeddings, OCR) |
| `MODELSTUDIO_DASHSCOPE_URL` | DashScope base URL (rerank only) |

All three are required. Startup must fail if any is missing.

URL format example (workspace-specific):
- OpenAI-compatible: `https://ws-<id>.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`
- DashScope: `https://ws-<id>.ap-southeast-1.maas.aliyuncs.com/api/v1`

---

### 17.2 Confirmed model names

| Role | Model name | API type |
|---|---|---|
| Classification | `qwen-plus` | OpenAI-compatible |
| Summarization | `qwen-plus` | OpenAI-compatible |
| Routing | `qwen-plus` | OpenAI-compatible |
| Escalation (ambiguous) | `qwen-max` | OpenAI-compatible |
| OCR | `qwen-vl-plus` | OpenAI-compatible (multimodal) |
| Embeddings | `text-embedding-v4` | OpenAI-compatible |
| Rerank | `qwen3-rerank` | DashScope (dedicated endpoint) |

**Important**: `gte-rerank-v2` is NOT available on workspace endpoints. Use `qwen3-rerank`.

Store model names in `api/config/models.yaml`, not hardcoded in source. Load them at runtime from config.

---

### 17.3 Client implementation

Use two clients:
1. `openai.OpenAI(api_key=..., base_url=MODELSTUDIO_BASE_URL)` — for chat, embeddings, OCR
2. `httpx.Client(timeout=120.0)` — for rerank via DashScope endpoint

#### Chat completion call pattern
```python
response = openai_client.chat.completions.create(
    model=model_config.model,
    messages=messages,                  # list[{"role": str, "content": str}]
    temperature=model_config.temperature,
    max_tokens=model_config.max_tokens,
)
content = response.choices[0].message.content
usage = response.usage  # .prompt_tokens, .completion_tokens, .total_tokens
finish_reason = response.choices[0].finish_reason
```

#### Structured JSON output — strip markdown fences
Models may return JSON wrapped in ` ```json ... ``` `. Must strip fences before parsing:
```python
content = response.strip()
if content.startswith("```"):
    lines = content.split("\n")
    inside = False
    json_lines = []
    for line in lines:
        if line.startswith("```"):
            inside = not inside
            continue
        if inside:
            json_lines.append(line)
    content = "\n".join(json_lines)
parsed = json.loads(content)
```

#### Embedding call pattern
```python
response = openai_client.embeddings.create(
    model="text-embedding-v4",
    input=texts,           # list[str]
    dimensions=1024,
)
# response.data[i].embedding  → list[float]
# response.usage.total_tokens → int
```

#### OCR call pattern (multimodal chat)
```python
response = openai_client.chat.completions.create(
    model="qwen-vl-plus",
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_base64}"},
            },
            {
                "type": "text",
                "text": "Please extract all text from this image. Return only the extracted text.",
            },
        ],
    }],
    temperature=0.0,
    max_tokens=2048,
)
text = response.choices[0].message.content or ""
```

#### Rerank call pattern (DashScope, raw httpx)
```python
payload = {
    "model": "qwen3-rerank",
    "input": {
        "query": query,
        "documents": documents,   # list[str]
    },
    "parameters": {
        "top_n": top_n,
        "return_documents": True,
    },
}
resp = httpx_client.post(
    f"{MODELSTUDIO_DASHSCOPE_URL}/services/rerank/text-rerank/text-rerank",
    headers={
        "Authorization": f"Bearer {MODELSTUDIO_API_KEY}",
        "Content-Type": "application/json",
    },
    json=payload,
)
if resp.status_code != 200:
    raise RuntimeError(f"Rerank API error: {resp.status_code} {resp.text}")
results = resp.json()["output"]["results"]
# Each result: {"index": int, "relevance_score": float, "document": {"text": str}}
```

---

### 17.4 Pydantic output schemas

All AI responses must be parsed into Pydantic models. Reject if parsing fails.

```python
class ClassificationResult(BaseModel):
    doc_type: str              # one of: cong_van, quyet_dinh, thong_bao, to_trinh, bao_cao, other
    confidence: float
    rationale: str
    issuing_agency: str | None = None
    urgency: str = "normal"   # normal | urgent | critical
    confidentiality: str = "unclassified"  # unclassified | confidential | secret | top_secret

class SummaryResult(BaseModel):
    summary_points: list[str]
    key_subject: str
    key_entities: list[str]

class RoutingResult(BaseModel):
    suggested_department: str
    secondary_department: str | None = None
    routing_confidence: float
    routing_rationale: str
    needs_consultation: bool = False
    needs_supervisor_review: bool = False

class EscalationResult(BaseModel):
    primary_recommendation: str
    alternatives: list[str]
    ambiguity_explanation: str
    confidence_per_department: dict[str, float]
    final_confidence: float
    needs_consultation: bool
    consultation_reason: str | None = None

class EmbeddingResult(BaseModel):
    embedding: list[float]
    model: str
    total_tokens: int

class RerankResult(BaseModel):
    index: int
    relevance_score: float
    text: str

class OCRResult(BaseModel):
    text: str
    page_count: int = 1
    extraction_method: str = "qwen-ocr"  # see note below
    warnings: list[str] = []
```

**`extraction_method` values — disambiguation**
- `"qwen-ocr"`: direct VL (`qwen-vl-plus`) call on a single image input (used by `ocr_adapter.ocr(image_bytes)`).
- `"render_ocr"`: `pdf2image` renders each PDF page to PNG, then each page is passed through the VL call; the `extracted_artifact` row carries `"render_ocr"`, not `"qwen-ocr"`, so the pipeline origin is preserved.
- `"pypdf"`: direct text extraction from a born-digital PDF, no AI call.
- `"docx"`, `"plaintext"`: deterministic text extraction from DOCX / TXT sources.

The `OCRResult` model is used by the adapter layer; the persistence layer maps it to `extracted_artifact.extraction_method` and may override the tag to `"render_ocr"` when called inside the PDF render pipeline.

---

### 17.5 Prompt templates

Prompts are stored as `.txt` files in `api/prompts/` with `{text}` and `{departments}` placeholders. Load at runtime, substitute before calling the model. Never embed prompts as string literals in source files.

Example prompt structure for classification:
```
Classify the following Vietnamese administrative document. Return ONLY a JSON object with these fields:

{
  "doc_type": "<one of: cong_van, quyet_dinh, thong_bao, to_trinh, bao_cao, other>",
  "confidence": <float between 0.0 and 1.0>,
  "rationale": "<brief explanation in English>",
  "issuing_agency": "<guessed issuing agency or null>",
  "urgency": "<one of: normal, urgent, critical>",
  "confidentiality": "<one of: unclassified, confidential, secret, top_secret>"
}

Document text:
---
{text}
---
```

For routing, inject the department list as `{departments}` with format `- {id}: {name}` per line.

---

### 17.6 Config file format

`api/config/models.yaml`:
```yaml
models:
  classify:
    model: "qwen-plus"
    api: "openai"
    temperature: 0.1
    max_tokens: 1024
  summarize:
    model: "qwen-plus"
    api: "openai"
    temperature: 0.3
    max_tokens: 512
  route:
    model: "qwen-plus"
    api: "openai"
    temperature: 0.1
    max_tokens: 1024
  escalate:
    model: "qwen-max"
    api: "openai"
    temperature: 0.2
    max_tokens: 2048
  ocr:
    model: "qwen-vl-plus"
    api: "openai"
    temperature: 0.0
    max_tokens: 2048
  embed:
    model: "text-embedding-v4"
    api: "openai"
    dimensions: 1024
  rerank:
    model: "qwen3-rerank"
    api: "dashscope"
    top_n: 5
```

---

### 17.7 Credential check implementation

`make check-credentials` must run a minimal live probe for each model:

| Model key | Check method |
|---|---|
| `classify` | `chat_completion([{"role":"user","content":"Say 'OK' and nothing else."}], max_tokens=10)` |
| `escalate` | Same as classify |
| `embed` | `embeddings(["test"])` |
| `ocr` | `ocr(base64_of_1x1_white_png)` |
| `rerank` | `rerank("test query", ["test document"], top_n=1)` |

**Return contract (locked).** The checker returns a dict with exactly these keys:

```
{
  "qwen-plus (classify)":      True | "FAILED: <msg>",
  "qwen-max (escalate)":       True | "FAILED: <msg>",
  "text-embedding-v4 (embed)": True | "FAILED: <msg>",
  "qwen-vl-plus (ocr)":        True | "FAILED: <msg>",
  "qwen3-rerank (rerank)":     True | "FAILED: <msg>",
}
```

Key format is `"{model_name} ({role_key})"`. Test plan §18.3 asserts these exact keys. `make check-credentials` exits non-zero if any value is not `True`.

---

### 17.8 PDF extraction strategy

For born-digital PDFs: use `pypdf` to extract text directly. Tag as `extraction_method="pypdf"`.

For scan-only PDFs (no embedded text): render pages to PNG with `pdf2image` (requires `poppler`), then call OCR. Tag as `extraction_method="render_ocr"` with a warning. If `pdf2image` is unavailable, fail explicitly.

Decision logic:
1. Try `pypdf` extraction.
2. If `has_text=False`, try `pdf2image` render + OCR per page (up to `max_pages=3`).
3. If both fail, return explicit error — do not fake successful extraction.

---

### 17.9 Test markers (pytest)

All AI adapter tests must use markers consistent with the reference pattern:

| Marker | Meaning | Gated by |
|---|---|---|
| `@pytest.mark.unit` | No API, runs in `make ci` | Always runs |
| `@pytest.mark.contract` | No API, schema checks, runs in `make ci` | Always runs |
| `@pytest.mark.mock_integration` | App-level integration, adapter stubbed, runs in `make ci` | Always runs |
| `@pytest.mark.live` | Real API call (per-adapter) | `--live` CLI flag |
| `@pytest.mark.creds` | Credential check | `--creds` CLI flag |
| `@pytest.mark.live_integration` | Full pipeline with real API | `--integration` CLI flag |

`conftest.py` (at `api/tests/conftest.py`) must gate `live`, `creds`, and `live_integration` tests behind CLI flags so `make test` (no flags) never calls external APIs. `mock_integration` tests use dependency-injected adapter stubs and always run in CI.

---

### 17.10 Prompt versioning scheme

- Prompt files live in `api/prompts/*.txt` and are loaded at process startup.
- The canonical `prompt_version.id` is the first **12 hex chars** of the SHA-256 of the raw file bytes (no whitespace trimming).
- The `prompt_version` table uses a composite primary key `(id, stage)` — see Pass 1 entity schema. The stage is derived from the file name (`classify.txt` → `stage="classify"`, etc.).
- On startup, `PromptRegistry` scans `api/prompts/`, computes each hash, and upserts a row for each `(id, stage)` pair.
- Every `ai_analysis` row stores `(prompt_version, stage)` as a foreign key pair into the registry.
- Optional human-readable labels live in `api/config/prompt_versions.yaml` (keyed by `{stage}/{id}` → label). Labels are informational only; the hash is the source of truth.
- Changing a prompt file produces a new `id` for that stage; old analyses remain queryable by their original `(id, stage)`.

---

### 17.11 Cached AI results storage (demo mode)

- Enabled only when `ENABLE_CACHED_AI_RESULTS=true` AND `ENABLE_DEMO_MODE=true`.
- Storage root: `CACHED_AI_STORAGE_ROOT` (default `data/cached_ai`).
- Path layout: `{root}/{prompt_version}/{stage}/{document_id}.json`.
- File schema:
  ```json
  {
    "prompt_version": "abc123def456",
    "stage": "classify",
    "model": "qwen-plus",
    "document_id": "...",
    "cached_at": "2026-04-01T10:00:00Z",
    "result": { "...validated pydantic dump..." }
  }
  ```
- Lookup rule: cache hit only when BOTH `prompt_version` AND `document_id` match; otherwise fall through to live call.
- The API response must include `"source": "cached" | "live"` on every AI result so UIs can label it.
- Cache writes happen via an explicit script (`scripts/seed_cached_ai.py`), never implicitly on a live call — this prevents accidental cache poisoning from noisy live runs.

---

### 17.12 Fence-stripping helper

The reference snippet in §17.3 is illustrative, not production-grade. The adapter must ship a tested helper `strip_json_fences(s: str) -> str` with the following contract:

- Input `{"a": 1}` → `{"a": 1}` (unchanged).
- Input ` ```json\n{"a":1}\n``` ` → `{"a":1}`.
- Input ` ```\n{"a":1}\n``` ` (no language tag) → `{"a":1}`.
- Input with surrounding whitespace is `.strip()`-ed before fence detection.
- Input `garbage` → returned unchanged (caller handles `json.JSONDecodeError`).
- Nested triple-backticks inside string literals must not break parsing; the helper only strips the outermost pair.

Contract tests for this helper are required in `api/tests/test_ai_contract.py`.
