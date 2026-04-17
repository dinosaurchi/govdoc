# GovDoc SecureFlow — Multi-Pass Implementation Plan

Version: 1.0  
Status: Implementation handoff note  
Primary input: `govdoc_source_of_truth_plan_v1_1.md`  
Scope: turn the existing Google AI Studio baseline (real frontend + backend, mocked business logic) into a real, testable MVP with Alibaba Model Studio integration, demo mode, and deterministic QA/deployment paths.

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
Explicitly validate Model Studio credentials and required model availability:
- simple `qwen-plus` generation call
- embedding call
- OCR call using a bundled small scan fixture
- optional `qwen-max` availability check if configured as enabled
Return non-zero on any failure.

#### `make up`
Run docker-compose locally and block on health checks.

#### `make qa`
Run local API/UI smoke checks after `make up`.

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
- `MODELSTUDIO_BASE_URL`
- `MODEL_CLASSIFY`
- `MODEL_ROUTE`
- `MODEL_SUMMARIZE`
- `MODEL_ESCALATE`
- `MODEL_OCR`
- `MODEL_EMBED`
- `MODEL_RERANK`
- `ENABLE_DEMO_MODE`
- `ENABLE_CACHED_AI_RESULTS`
- `ENABLE_LIVE_OCR`
- `ENABLE_LIVE_EMBEDDINGS`
- `LOCAL_FILE_STORAGE_ROOT`
- `PROMPT_CONFIG_PATH`
- `REMOTE_HOST`
- `REMOTE_USER`
- `REMOTE_APP_DIR`

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
11. `make lint`, `make build`, `make test`, `make ci`, `make up`, `make qa`, and `make up-remote` all exist and behave deterministically
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
