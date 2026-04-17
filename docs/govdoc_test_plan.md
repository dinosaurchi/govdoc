# GovDoc SecureFlow — Multi-Pass Test Plan

Version: 1.1.1  
Status: Verification handoff note  
Primary input: `govdoc_source_of_truth_plan_v1_1.md`  
Paired with: `govdoc_implementation_plan.md` (v1.1.1)

Changelog since 1.1:
- Rewrote §4.1 `make check-credentials` to match the locked 5-mandatory-model probe contract in implementation plan §17.7 (removed "optional escalate").

Changelog since 1.0:
- Committed to Playwright (removed "or equivalent").
- Added `make test-e2e` intent block (§4.1) and expanded remote QA checklist with concrete commands (§12).
- Rephrased AI quality thresholds as ratios and added `summary_expectations.jsonl` schema (§7.3, §7.3.1).
- Split `integration` marker into `mock_integration` (CI-safe) and `live_integration` (gated); pinned `conftest.py` location to `api/tests/conftest.py` (§18.1).
- Added RBAC (role × endpoint) matrix requirement (Pass 6) and retrieval quality thresholds + prompt-version traceability test (Pass 7).

---

## 1) Goal

Verify that the GovDoc SecureFlow MVP is:

- correct enough for the selected use-case
- honest about uncertainty and failure
- stable to demo
- deployable locally and remotely
- backed by repeatable tests
- integrated with Alibaba Model Studio in a visible and verifiable way

This plan covers:

- unit tests
- integration tests
- API contract tests
- AI credential checks
- AI result quality tests
- Web UI / Playwright tests
- local QA
- remote deploy QA

---

## 2) Non-negotiable test rules

1. **Fail fast**
   - first failing stage returns non-zero
   - no “soft pass” unless explicitly marked informational

2. **No hiding error**
   - tests must fail if the app silently falls back to fake outputs in normal mode
   - tests must fail if the app claims success after an AI or workflow error

3. **Deterministic by default**
   - `make test` must be deterministic and must not depend on live external credentials
   - live Model Studio checks belong in `make check-credentials` and `make test-ai`

4. **Separate static/deterministic tests from live-AI tests**
   - CI-safe tests and live-AI tests must be clearly separated

5. **Every implementation pass needs a verification gate**
   - no pass is complete without its paired tests

---

## 3) Test layers

### Layer A — Static quality
- lint
- type checks
- formatting checks
- schema consistency
- no-dead-import / build-time correctness

### Layer B — Unit tests
Pure logic tests for:
- config loading
- workflow transitions
- permission policy
- file validation
- extraction helpers
- AI output parsing/validation
- threshold decisions
- prompt version resolution
- remote deploy command assembly

### Layer C — Integration tests
App-level tests for:
- persistence
- API endpoints
- workflow transitions
- record creation
- consultation writes
- evidence retrieval
- demo scenario loading

### Layer D — Contract tests
Verify backend response shapes and frontend/backend contracts for:
- document record shape
- AI analysis shape
- routing decision shape
- audit event shape
- health endpoints

### Layer E — Live credential checks
Validate:
- API key works
- correct base URL works
- required models are reachable

### Layer F — AI result quality tests
Measure:
- type classification quality
- routing quality
- ambiguity handling
- summary structure/coverage
- OCR viability on scan fixtures
- out-of-scope handling

### Layer G — End-to-end UI tests
Playwright:
- hero flow
- ambiguity flow
- scan flow
- error surfacing flow

### Layer H — Deployment QA
- local `make up`
- local `make qa`
- remote `make up-remote`
- remote health verification

---

## 4) Required test-related Make targets

At minimum:

- `make test`
- `make test-ai`
- `make test-e2e`
- `make check-credentials`
- `make qa`
- `make ci`

### 4.1 Required behaviors

#### `make test`
Must run:
- unit tests
- deterministic integration tests
- contract tests

Must not require live Model Studio credentials.

#### `make check-credentials`
Must verify, per the locked 5-model probe contract in implementation plan §17.7, that all of the following succeed (all are mandatory; none are optional):
- `qwen-plus (classify)` — short generation call
- `qwen-max (escalate)` — short generation call
- `text-embedding-v4 (embed)` — embedding call on a trivial input
- `qwen-vl-plus (ocr)` — OCR call on the bundled 1×1 white PNG fixture
- `qwen3-rerank (rerank)` — rerank call with a single document on the DashScope endpoint

Env validation (`MODELSTUDIO_API_KEY`, `MODELSTUDIO_BASE_URL`, `MODELSTUDIO_DASHSCOPE_URL`) runs first; missing or empty values fail before any HTTP call is made.

#### `make test-ai`
Must run live AI quality evaluation against the bundled data pack and produce machine-readable results.

#### `make test-e2e`
Must run the Playwright suite (`web/tests-e2e/`) against the running local docker-compose environment.

Preconditions:
- `make up` must have completed (`readyz` returns healthy) before `make test-e2e` starts.
- If the stack is not reachable at `http://localhost:${WEB_PORT}`, the target must fail fast without running tests.

Outputs:
- `data/e2e-report/` HTML report.
- `data/e2e-report/screenshots/` on failure.

#### `make qa`
Must run smoke checks after `make up`.

---

## 5) Test fixtures and datasets

### 5.1 Primary corpus
Use the bundled full pack:
- `incoming/`
- `hard-cases/`
- `reference-corpus/`
- `labels/`

### 5.2 Minimal deterministic fixtures
Add small repo-local deterministic fixtures for:
- valid born-digital PDF
- invalid file
- empty file
- tiny scan fixture
- malformed AI output sample
- ambiguous routing sample
- out-of-scope sample

### 5.3 Seeded scenarios
At minimum:
- hero
- ambiguity
- scan
- out-of-scope

---

## 6) Pass-by-pass verification plan

---

## Pass 0 verification — Baseline audit and repo hardening

### Tests to add/run
- smoke build test
- health endpoint test
- config-loader unit tests
- docker-compose config validation
- baseline mock-path detection test where applicable

### Acceptance criteria
- repo boots locally
- health endpoint works
- bad config fails startup
- no hidden generic success state in baseline paths
- `make lint`, `make build`, `make test` execute meaningfully

---

## Pass 1 verification — Domain model, workflow engine, persistence

### Unit tests
- valid workflow transitions
- invalid workflow transitions
- audit-event emission on every mutation
- role action matrix
- security-level visibility policy

### Integration tests
- create document record
- advance workflow through valid states
- reject illegal state transition
- role-based forbidden action returns explicit failure

### Acceptance criteria
- workflow rules enforced server-side
- every mutation produces audit event
- role restrictions tested and passing
- invalid transitions do not mutate state

---

## Pass 2 verification — File intake, storage, deterministic extraction

### Unit tests
- allowed file validation
- disallowed extension rejection
- empty file rejection
- corrupt file rejection
- deterministic extraction helper behavior

### Integration tests
- upload valid born-digital PDF
- persist raw file reference
- persist extracted artifact
- extraction failure path returns explicit error

### Acceptance criteria
- valid upload creates correct persisted records
- unsupported/corrupt files fail clearly
- extracted artifact stored separately from raw file
- no AI stage starts if extraction failed

---

## Pass 3 verification — Credentials and Model Studio adapter

### Unit tests
- adapter request builder
- adapter error normalization
- structured response parser
- credential-check command builder

### Live checks
`make check-credentials` must verify:
- invalid key => fail
- wrong base URL => fail
- valid key + valid base URL => success
- required model missing => fail

### Acceptance criteria
- all adapter failures are classified and visible
- `make check-credentials` is trustworthy and explicit
- success path proves actual connectivity, not just env presence

---

## Pass 4 verification — Core AI analysis pipeline

### Unit tests
- AI JSON schema validator
- malformed AI response rejection
- threshold-based escalation decision
- prompt version tagging

### Integration tests
- run analysis on deterministic extracted fixture with mocked adapter
- persist AI analysis record
- reject malformed analysis payload
- escalation path writes separate metadata

### Acceptance criteria
- AI analysis cannot bypass schema validation
- malformed outputs fail loudly
- persisted analysis includes model + prompt metadata
- routing suggestion is not directly treated as final state

---

## Pass 5 verification — OCR and hard-case path

### Unit tests
- scan detection heuristics
- OCR path selection
- out-of-scope flag logic
- hard-case marker logic

### Live AI tests
Use bundled scan fixtures to verify:
- OCR returns non-empty extraction
- OCR output enters normal analysis flow
- OCR failure is surfaced honestly

### Acceptance criteria
- scan fixtures use OCR path
- OCR failure path is visible and testable
- out-of-scope cases are not forced into false in-scope certainty

---

## Pass 6 verification — Review, consultation, and closeout workflow

### Unit tests
- approve/reject/reroute action logic
- consultation request rules
- supervisor escalation rules
- closeout transition rules

### Integration tests
- hero flow backend progression
- consultation thread persistence
- supervisor visibility path
- unauthorized action rejection

### Acceptance criteria
- hero flow fully works through backend APIs
- consultation state is persisted and queryable
- role-based actions enforced
- closeout state reachable only through valid workflow path

### RBAC endpoint matrix (required)

A parametrized test (`test_rbac_matrix.py`) must assert the full (role × endpoint) matrix for every protected endpoint listed in implementation plan §Pass 6. For each cell the test sends the request with `X-GovDoc-Role: <role>` and asserts either `allowed` (non-2xx only for unrelated reasons) or `forbidden` (403 `FORBIDDEN_ACTION`).

Minimum matrix (expand as new endpoints are added):

| Endpoint | intake_clerk | reviewer | supervisor |
|---|---|---|---|
| `POST /documents` (upload) | allow | allow | allow |
| `POST /documents/{id}/analyze` | deny | deny | allow |
| `POST /documents/{id}/approve-routing` | deny | allow | allow |
| `POST /documents/{id}/reroute` | deny | allow | allow |
| `POST /documents/{id}/request-consultation` | deny | allow | allow |
| `POST /documents/{id}/resolve-consultation/*` | deny | allow | allow |
| `POST /documents/{id}/escalate` | deny | deny | allow |
| `POST /documents/{id}/mark-out-of-scope` | deny | allow | allow |
| `POST /documents/{id}/close` | deny | deny | allow |
| `POST /demo/reset` | deny | deny | allow (dev env only) |

Missing / unknown role tests:
- no `X-GovDoc-Role` header → `400 MISSING_ROLE_HEADER`
- `X-GovDoc-Role: ghost` → `403 UNKNOWN_ROLE`

---

## Pass 7 verification — Retrieval, evidence panel, prompt versioning, demo mode

### Unit tests
- reference chunk selection
- retrieval request building
- evidence-panel formatting
- cached/live result labeling

### Integration tests
- reference corpus load
- retrieval endpoint returns ranked items
- prompt version lookup works
- demo mode loads seeded scenario
- cached AI result path is explicitly marked

### Acceptance criteria
- evidence panel is populated for at least seeded scenarios
- cached/live distinction is test-covered
- retrieval failure does not silently fake good evidence

### Retrieval quality thresholds

- Default `top_k = 5` for `POST /retrieval/search` tests.
- For each seeded scenario with a labeled relevant reference, the relevant chunk must appear in the top-k returned list (**recall@5 = 1.00** on the seeded set).
- Reranked score ordering must be strictly non-increasing: `scores[i] >= scores[i+1]` for all `i`.
- For a handcrafted pair (one near-duplicate, one unrelated), the cosine similarity gap must exceed `0.15` to catch embedding-endpoint regressions.

### Prompt version traceability test

- Hash two distinct prompt files; assert both ids are registered and distinct.
- Modify one prompt file by a single byte, reload the registry, assert a new hash id appears.
- Assert every `ai_analysis` row written during integration tests carries a `prompt_version` present in the registry.

---

## Pass 8 verification — Deployment and QA

### Local QA
After `make up`:
- API health endpoint
- web reachable
- upload smoke path
- one seeded scenario visible
- logs accessible

### Remote QA
After `make up-remote`:
- remote health endpoint
- remote web reachable
- one seeded API query succeeds
- remote logs accessible
- failure leaves explicit diagnostics

### Acceptance criteria
- `make up` is enough to boot local demo environment
- `make qa` catches obvious boot/config issues
- `make up-remote` is trustworthy and fails fast
- deployment success is defined by real health checks, not command completion alone

---

## 7) AI result quality evaluation plan

This is a required test area, not optional.

### 7.1 Scope
Evaluate on:
- in-scope incoming docs
- hard cases
- scan cases
- out-of-scope cases

### 7.2 Metrics

#### A. Classification accuracy
Measure:
- exact-match doc type accuracy
- exclude documents explicitly labeled out-of-scope when computing in-scope accuracy

#### B. Routing quality
Measure:
- top-1 department accuracy
- top-2 acceptable routing accuracy
- multi-department hard-case handling

#### C. Summary quality
Measure:
- schema validity
- non-empty summary
- bullet count / format compliance
- coverage of expected key points from `summary_expectations.jsonl`

#### D. OCR viability
Measure:
- non-empty extraction rate
- downstream classification success after OCR

#### E. Uncertainty honesty
Measure:
- hard cases should trigger:
  - lower confidence
  - consultation recommendation
  - supervisor review flag
  where appropriate

### 7.3 Initial bootstrap thresholds

These are practical hackathon thresholds. They are expressed as **ratios over the evaluated subset** rather than absolute counts so they remain valid as the bundled corpus grows or shrinks. The actual subset size is read from `data/labels/*.jsonl` at test time and recorded in the report.

- classification exact-match on in-scope docs: **>= 0.70**
- routing top-1 on labeled cases: **>= 0.60**
- routing top-2 on labeled cases: **>= 0.80**
- summary schema validity: **1.00**
- summary coverage score: **>= 0.70**
- OCR non-empty extraction on scan fixtures: **>= 0.85**
- ambiguity flagging on multi-department hard cases: **>= 0.80**
- out-of-scope honesty on out-of-scope cases: **>= 0.65**

The generated report must include both the ratio and the absolute numerator/denominator (e.g. `0.875 (7/8)`). These are minimum thresholds, not final aspirational ceilings.

### 7.3.1 Expected-points label file

Summary coverage is computed against `data/labels/summary_expectations.jsonl`, one JSON object per line:

```json
{
  "doc_id": "hero-001",
  "expected_points": ["decision authority", "effective date", "affected agencies"],
  "min_coverage": 0.7
}
```

- `doc_id`: matches the `document.id` of a seeded scenario document.
- `expected_points`: list of short Vietnamese/English phrases that should appear (substring, case-insensitive) across the generated `summary_points`.
- `min_coverage`: per-document override; falls back to §7.3 if absent.

Missing label file → `make test-ai` treats summary coverage as "not evaluated" and logs a warning; it does not hard-fail on coverage alone unless the file exists.

### 7.4 Reporting format

`make test-ai` must emit:
- machine-readable JSON
- human-readable markdown summary
- per-document detail rows for failures
- aggregate metrics by category

### 7.5 Hard fail vs soft fail

Hard fail:
- credential check fails
- summary schema validity < 1.00
- OCR path completely broken
- zero ambiguity handling
- malformed output accepted as success

Soft fail / warning:
- accuracy below stretch target but above minimum threshold

---

## 8) Required unit test inventory

At minimum, unit tests must exist for:

- env/config validation
- workflow transition rules
- role permission matrix
- security-level visibility logic
- file validation
- extraction method selection
- OCR-path selection
- AI request builder
- AI response schema validator
- threshold/escalation logic
- prompt version resolution
- evidence retrieval formatting
- deployment variable validation
- remote deploy command assembly

---

## 9) Required integration test inventory

At minimum, integration tests must exist for:

- upload born-digital file
- create/persist document record
- create/persist extracted artifact
- run analysis pipeline with adapter stub
- persist AI analysis
- approve routing
- reroute document
- request consultation
- complete consultation
- close document
- retrieve evidence panel
- load seeded scenarios
- reject unauthorized role action
- reject invalid workflow transition

---

## 10) Required E2E/UI scenarios

At minimum, Playwright must cover:

### Scenario 1 — Hero flow
- open app
- choose intake clerk role
- upload hero doc
- wait for analysis
- inspect detail page
- approve routing
- switch reviewer role
- request consultation
- switch supervisor role
- confirm timeline progression

### Scenario 2 — Ambiguity flow
- open seeded ambiguous doc
- verify lower confidence or consultation flag
- reroute or escalate
- verify audit log update

### Scenario 3 — Scan flow
- upload or open seeded scan case
- verify OCR path shown
- verify analysis results rendered
- verify warnings visible if applicable

### Scenario 4 — Error surfacing flow
- simulate or trigger AI failure
- verify explicit UI error state
- verify document not falsely marked analyzed

---

## 11) QA smoke checklist (`make qa`)

`make qa` should at minimum verify:

- web responds
- api responds
- health endpoint returns healthy
- one seeded scenario is loaded
- one upload endpoint is reachable
- one record detail endpoint is reachable
- logs endpoint or local logs are available

---

## 12) Remote deployment QA checklist

After `make up-remote`, verify:

- remote containers running: `ssh ${REMOTE_USER}@${REMOTE_HOST} "cd ${REMOTE_APP_DIR} && docker compose ps --format json"` — all services `running`/`healthy`
- remote health endpoint healthy: `curl -fsS http://${REMOTE_HOST}:${APP_PORT}/readyz` returns 200 with `{"status":"ok"}`
- remote UI reachable: `curl -fsS http://${REMOTE_HOST}:${WEB_PORT}/` returns 200 and contains the app title
- one API smoke request passes: `curl -fsS -H "X-GovDoc-Role: intake_clerk" http://${REMOTE_HOST}:${APP_PORT}/meta/roles` returns the seeded role list
- one seeded scenario visible: `GET /demo/scenarios` returns at least the `hero` scenario
- logs retrievable: `ssh ${REMOTE_USER}@${REMOTE_HOST} "cd ${REMOTE_APP_DIR} && docker compose logs --tail 200 --no-color"` streams without error and is captured to `data/remote-qa/logs-<timestamp>.txt` by the caller

Each check above is a discrete step in `scripts/remote_qa.sh`. Any non-zero step fails the deploy; the script prints the failing step id and the captured output path.

If any check fails, `make up-remote` must exit non-zero.

---

## 13) Regression policy

Every bug fixed during implementation must add at least one regression test in the smallest layer that can reproduce it:

- unit if logic-only
- integration if API/workflow/persistence related
- E2E if UI behavior/regression only reproducible through full flow

---

## 14) Reporting expectations

The test suite should produce outputs that make failures easy to diagnose.

### Required artifacts
- unit/integration report
- AI quality metrics report
- E2E report/screenshots on failure
- deploy QA summary
- remote deploy log bundle or printed step logs

---

## 15) Pass-by-pass acceptance summary

### Pass 0
Repo scaffolding and baseline behavior validated.

### Pass 1
Workflow core verified.

### Pass 2
Intake/extraction verified.

### Pass 3
Credentials and adapter verified.

### Pass 4
AI pipeline verified.

### Pass 5
OCR/hard-case behavior verified.

### Pass 6
Human review workflow verified.

### Pass 7
Retrieval/demo mode verified.

### Pass 8
Local/remote deployment verified.

---

## 16) Overall acceptance criteria

The testing phase is complete only when:

1. `make lint`, `make build`, `make test`, `make ci`, `make check-credentials`, `make up`, `make qa`, `make test-ai`, `make test-e2e`, and `make up-remote` all exist and behave as documented
2. deterministic tests pass without external credentials
3. credential checks prove real Model Studio access
4. AI quality report is generated on the bundled full pack
5. minimum bootstrap thresholds are met or any shortfall is explicit and documented
6. UI/E2E flows cover hero, ambiguity, scan, and failure paths
7. local deployment passes smoke QA
8. remote deployment passes smoke QA
9. no hidden-error or fake-success paths remain untested
10. failures are diagnosable from logs/reports

---

## 17) Explicit anti-patterns that must fail tests

The following behaviors should cause test failure:

- silent fallback to fake AI results in normal mode
- workflow state mutation without audit event
- accepting malformed AI JSON as valid
- pretending OCR succeeded with empty extraction
- allowing unauthorized role action
- hiding deployment failure behind successful command exit
- reporting healthy state when a required dependency is not healthy
- returning demo cached results without clear labeling

---

## 18) Model Studio integration test specification

This section is concrete and prescriptive, derived from the validated `alibaba-api-test` reference repo. Implement these tests exactly.

---

### 18.1 pytest marker setup (`api/tests/conftest.py`)

The conftest lives at `api/tests/conftest.py` (the api-side pytest root). Playwright E2E tests live under `web/tests-e2e/` and are run via `npx playwright test`, not pytest.

```python
def pytest_configure(config):
    config.addinivalue_line("markers", "unit: unit tests (no external API)")
    config.addinivalue_line("markers", "contract: contract tests (no external API)")
    config.addinivalue_line("markers", "mock_integration: app-level integration with stubbed AI adapter (no external API)")
    config.addinivalue_line("markers", "live: live API tests (requires credentials)")
    config.addinivalue_line("markers", "creds: credential validation tests")
    config.addinivalue_line("markers", "live_integration: full pipeline with real API (requires credentials)")

def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False)
    parser.addoption("--creds", action="store_true", default=False)
    parser.addoption("--integration", action="store_true", default=False)

def pytest_collection_modifyitems(config, items):
    for item in items:
        if "live" in item.keywords and not config.getoption("--live", default=False):
            item.add_marker(pytest.mark.skip(reason="Need --live flag"))
        if "creds" in item.keywords and not config.getoption("--creds", default=False):
            item.add_marker(pytest.mark.skip(reason="Need --creds flag"))
        if "live_integration" in item.keywords and not config.getoption("--integration", default=False):
            item.add_marker(pytest.mark.skip(reason="Need --integration flag"))
```

**Marker routing:**

| Target | Markers included | External API? |
|---|---|---|
| `make test` | `unit`, `contract`, `mock_integration` | No |
| `make ci` | same as `make test` (+ lint, build) | No |
| `make check-credentials` | `creds` only (pytest `--creds`) | Yes |
| `make test-ai` | `live`, `live_integration` (pytest `--live --integration`) | Yes |

`mock_integration` tests must use the FastAPI dependency-override mechanism to swap the Model Studio adapter for a deterministic stub. They run in CI.

---

### 18.2 Contract tests (no API — run in `make ci`)

File: `api/tests/test_ai_contract.py` marked `@pytest.mark.contract`

Required tests:

**Schema validation**
- `ClassificationResult` parses a valid dict
- `ClassificationResult` rejects missing `doc_type`
- `SummaryResult` requires non-empty `summary_points`
- `RoutingResult` requires `suggested_department`
- `EscalationResult` requires `primary_recommendation` and `alternatives`
- `OCRResult` defaults `extraction_method="qwen-ocr"` and `warnings=[]`
- `EmbeddingResult` parses `embedding: list[float]`
- `RerankResult` parses `index`, `relevance_score`, `text`

**JSON fence stripping**
- Input ` ```json\n{"key": "value"}\n``` ` → parses correctly
- Input `{"key": "value"}` (no fences) → parses correctly
- Input `garbage non-json` → raises `json.JSONDecodeError`

**Config loading**
- `models.yaml` contains all 7 required keys: `classify`, `summarize`, `route`, `escalate`, `ocr`, `embed`, `rerank`
- `classify.model == "qwen-plus"`, `escalate.model == "qwen-max"`, `embed.model == "text-embedding-v4"`, `rerank.model == "qwen3-rerank"`
- Missing `MODELSTUDIO_API_KEY` raises `ValueError` at config load time
- Missing `MODELSTUDIO_BASE_URL` raises `ValueError`
- Missing `MODELSTUDIO_DASHSCOPE_URL` raises `ValueError`

**Prompt files**
- `prompts/classify.txt` contains `{text}` and `doc_type`
- `prompts/summarize.txt` contains `{text}` and `summary_points`
- `prompts/route.txt` contains `{text}` and `{departments}`
- `prompts/escalate.txt` contains `{text}` and `ambiguity`
- Missing prompt file raises `FileNotFoundError`

---

### 18.3 Credential check tests (requires `--creds`)

File: `api/tests/test_live_creds.py` marked `@pytest.mark.creds`

Required tests — each must pass individually:

```python
def test_qwen_plus_available(client):
    results = client.check_credentials()
    assert results["qwen-plus (classify)"] is True

def test_qwen_max_available(client):
    results = client.check_credentials()
    assert results["qwen-max (escalate)"] is True

def test_embedding_available(client):
    results = client.check_credentials()
    assert results["text-embedding-v4 (embed)"] is True

def test_ocr_available(client):
    results = client.check_credentials()
    assert results["qwen-vl-plus (ocr)"] is True

def test_rerank_available(client):
    results = client.check_credentials()
    assert results["qwen3-rerank (rerank)"] is True
```

If any test fails, `make check-credentials` must exit non-zero.

---

### 18.4 Live API tests (requires `--live`)

File: `api/tests/test_live_api.py` marked `@pytest.mark.live`

**Chat completions**
- Basic generation returns non-empty `content` and `usage.total_tokens > 0`
- JSON output: request `{"status": "ok", "number": 42}` → parsed correctly
- Vietnamese text: send Vietnamese prompt, verify non-empty response
- Unknown model name raises `ValueError` with message "Unknown model"
- `qwen-max` responds to same prompt

**Embeddings**
- Single text → `len(embedding) > 0`, `model` field populated
- Batch of 3 texts → 3 results
- Vietnamese text (`"Cong van so 123/UBND-VP"`) → embedding returned
- Embedding dimension is 1024 (as configured)
- Similarity ordering: two similar Vietnamese texts score higher than one unrelated text

**OCR**
- White image with text → non-empty `text` returned
- `extraction_method == "qwen-ocr"`
- Empty response for blank image does not raise (must handle gracefully)

**Rerank**
- Query + 3 candidates → results in descending `relevance_score` order
- Single candidate → 1 result
- Vietnamese query + Vietnamese documents → reranked correctly
- Non-200 response raises `RuntimeError`

---

### 18.5 Integration pipeline tests (requires `--integration`)

File: `api/tests/test_ai_pipeline.py` marked `@pytest.mark.live_integration`

**Classification pipeline**
- Extract text from fixture `cong_van` → classify → `doc_type` is one of 6 valid types → `confidence > 0.5`
- Classify returns `rationale` (non-empty string)

**Summarization pipeline**
- Summarize fixture text → `len(summary_points) >= 2` → `key_subject` non-empty

**Routing pipeline**
- Route fixture text with department list → `suggested_department` in valid department IDs → `routing_confidence > 0`

**Escalation pipeline**
- Escalate ambiguous text → `primary_recommendation` in dept IDs → `final_confidence > 0` → `ambiguity_explanation` non-empty → `len(alternatives) >= 1`

**Retrieval pipeline**
- Embed 3 candidate texts + query → cosine similarity returns top-k correctly ordered
- Most similar pair has higher similarity than unrelated pair

**Full pipeline (extract → classify → summarize → route)**
- Fixture cong_van PDF: extract text → classify → summarize → route
- All three results non-empty
- Entire pipeline completes without exception

---

### 18.6 PDF extraction tests (no API)

File: `api/tests/test_extraction.py` marked `@pytest.mark.unit`

- Born-digital PDF → `has_text=True`, `extraction_method="pypdf"`, `page_count >= 1`
- Scan-only PDF (no embedded text) → `has_text=False` from `pypdf`
- Missing file → `FileNotFoundError`
- `extract_text_or_ocr` on born-digital → returns pypdf result (no OCR call)
- `extract_text_or_ocr` on scan-only → calls OCR adapter (mock it), records `extraction_method="render_ocr"` and warns

---

### 18.7 Error handling tests

File: `api/tests/test_ai_errors.py` marked `@pytest.mark.unit`

All with mocked adapter:

- Adapter raises `openai.AuthenticationError` → normalized as `ModelStudioAuthError`
- Adapter raises `openai.NotFoundError` (model unavailable) → normalized as `ModelStudioModelUnavailableError`
- Adapter raises `openai.RateLimitError` → normalized as `ModelStudioRateLimitError`
- Adapter returns valid JSON but wrong schema → `pydantic.ValidationError` raised, not swallowed
- Adapter returns non-JSON content → `json.JSONDecodeError` raised, not swallowed
- Rerank endpoint returns 401 → `RuntimeError` with status code in message
- Rerank endpoint returns 404 → `RuntimeError` with status code in message

---

### 18.8 Test fixtures required

Minimal fixtures in `api/tests/fixtures/`:

| File | Content |
|---|---|
| `sample_cong_van.txt` | Plain-text Vietnamese cong van (born-digital) |
| `sample_departments.json` | `{"departments": [{"id": "...", "name": "..."}, ...]}` (min 5 depts) |
| `malformed_ai_response.txt` | Non-JSON string to test parse rejection |
| `white_10x10.png` | Minimal PNG for OCR credential check |

---

### 18.9 `make test-ai` output format

Must emit to stdout and a file (`data/ai_quality_report.json`):

```json
{
  "timestamp": "ISO-8601",
  "summary": {
    "classification_accuracy": 0.0,
    "routing_top1_accuracy": 0.0,
    "routing_top2_accuracy": 0.0,
    "summary_schema_valid_rate": 0.0,
    "ocr_success_rate": 0.0,
    "ambiguity_flagged_rate": 0.0
  },
  "failures": [
    {"file": "...", "expected": "...", "got": "...", "error": "..."}
  ]
}
```

Hard fail thresholds (exit non-zero):
- `summary_schema_valid_rate < 1.0`
- `ocr_success_rate == 0.0`
- any adapter error accepted as success
