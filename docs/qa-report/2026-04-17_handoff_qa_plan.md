# GovDoc SecureFlow — QA Handoff Plan (2026-04-17)

**Branch under test:** `chi/implement-core-logic`
**Author:** Claude (post code-fix pass)
**Stack state when writing:** `make up` stack healthy; backend API hero flow fully verified via curl with live Model Studio (Qwen). Mock providers have been removed — live credentials are now required to run the stack.

This document lists **what still needs human QA** after the automated tests and backend smoke tests that Claude already ran. Use it as a checklist: each scenario has a preconditions block, a step list, and explicit pass/fail criteria.

---

## 0 — What's already covered (do not re-test, only re-confirm if broken)

These were verified during the fix pass and are green:

- [x] `make ci` — 202 tests pass, docker images build.
- [x] Backend API hero flow via curl **with live Qwen** (upload → analyzed → routed → under_review → approved → closed); all `AIAnalysis.source == "live"`.
- [x] RBAC matrix (intake_clerk close → 403, missing role → 400, ghost role → 403, demo/reset reviewer → 403, supervisor → 200).
- [x] Out-of-scope branch via API (`POST /mark-out-of-scope`).
- [x] Per-stage idempotent re-analyze (`POST /documents/{id}/analyze` returns cached 3 stages).
- [x] Prompt versions are real SHA-256[:12] hashes on live intake (was `"unknown"` before the fix).
- [x] Mock providers deleted; fail-fast verified (stripping `MODELSTUDIO_API_KEY` raises `ValueError` immediately on startup).
- [x] Retrieval service wired to live `text-embedding-v4` embed function via `RealAIProvider`.

If any of the above regress, the fix pass broke something; investigate first before proceeding with the sections below.

---

## 1 — Environment setup (do this once before any QA run)

### 1.1 Start the stack
```bash
cd /workspace/projects/hackathon/2026-qwen-ai-build-day/govdoc
rm -f data/secureflow.db api/data/secureflow.db   # reset DB for a clean run
make up                                            # builds and brings up api + web
```

### 1.2 Confirm reachability
In sandboxed environments, `localhost:8000` may be blocked. Use the docker network gateway:

```bash
docker network inspect govdoc_default --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}'
# Typical output: 172.23.0.1
```

Then:
```bash
API=http://172.23.0.1:8000
WEB=http://172.23.0.1:3000
curl -sf $API/healthz && curl -sf $API/readyz && curl -s -o /dev/null -w "%{http_code}\n" $WEB/
# Expect: {"status":"ok"} {"status":"ok"} 200
```

On a workstation with normal networking, `http://localhost:8000` and `http://localhost:3000` work directly.

### 1.3 Seed demo data (optional but recommended for the demo-scenarios section)
```bash
make seed-demo
```
This creates three seed documents with canned AI analyses. Expect `seed_demo_data: created/updated seeded documents: [...]` with three UUIDs.

---

## 2 — Web UI golden path (the hero demo) — **MUST DO**

> Claude never actually opened the browser. This is the single highest-risk area and must be click-tested before any live demo.

### 2.1 Scenario: intake clerk uploads → reviewer approves + consults → supervisor closes

**Preconditions:** Fresh DB (`rm data/secureflow.db && make up`). A sample text or PDF file. You can use:
- `api/tests/fixtures/sample_cong_van.txt` (Vietnamese admin letter)
- Any `.pdf` you have on hand

**Steps:**
1. Open `http://<host>:3000/` in a browser (Chrome/Firefox). Confirm the landing page renders without a white screen.
2. On the role switcher (top-right or in the header), select **Intake Clerk**. Confirm the role badge updates.
3. Navigate to **/intake** (or click the "Intake" nav link).
4. Drag-drop or file-select `sample_cong_van.txt`. Click Upload.
5. Switch the role to **Department Reviewer**.
6. Navigate to **/review** (or click "Review"). Confirm the newly uploaded doc appears in the list with `status = analyzed` or `routed`.
7. Click into the document row (navigates to `/documents/<id>`).
8. Click **Approve routing**. Confirm status updates to `routed`. Refresh: confirm the implicit `routed → under_review` claim has happened (status should show `under_review`).
9. Click **Request consultation** (with a body like "Xin y kien"). Confirm the consultation note shows in a thread, status is `in_consultation`.
10. Switch the role to **Supervisor**. Navigate back to the document.
11. Click **Resolve consultation** on the open note. Confirm status returns to `under_review`.
12. Click **Close document**. Confirm status becomes `closed`.

**Pass criteria:**
- All six status transitions show up visibly in the UI without a page refresh being required.
- No console errors in the browser devtools console at any step.
- The document list filter (`/review`) reflects each status change within a reasonable refresh.

**Fail modes to watch for:**
- Buttons present but clicking them does nothing (likely: API shape mismatch between frontend and `response_model` I added).
- "Unknown role" toast when switching to Consultant — this is a **known bug**, see §4.1.
- Status label stuck on `analyzed` after Approve routing — probably the frontend isn't re-fetching; refresh and check the API directly.

### 2.2 Recovery from failure
If something looks wrong in the UI, verify the same flow via curl (the API was fully verified — see handoff plan §0). If curl works but UI doesn't, the gap is on the frontend side.

```bash
# Upload
curl -sf -X POST $API/api/v1/documents/ -H 'X-GovDoc-Role: intake_clerk' \
  -F "file=@api/tests/fixtures/sample_cong_van.txt" | python3 -m json.tool
```

---

## 3 — Web UI edge cases and error paths

### 3.1 Missing role header
**Steps:** Clear `localStorage` (`localStorage.clear()` in devtools), reload `/review`, and observe behavior.
**Expected:** The UI either forces role selection on first visit, or hits the API without header → 400 MISSING_ROLE_HEADER → shown as a user-friendly toast.
**Pass criteria:** No silent failure; user is nudged to pick a role.

### 3.2 Forbidden actions in the UI
**Steps:**
1. As **Intake Clerk**, open a document detail page.
2. Attempt to click Approve routing / Request consultation / Close (if the buttons are visible).
**Expected:** Either the buttons are hidden for intake_clerk (preferred), or clicking surfaces a 403 FORBIDDEN_ACTION toast.
**Fail:** Silent failure or cryptic error.

### 3.3 Upload rejections
**Steps:**
1. As Intake Clerk, try uploading an empty file (`touch empty.bin && upload`).
2. Try uploading an unsupported type (`.exe`, `.tar.gz`).
3. Try uploading an oversized file (spec usually caps at 20 MB — verify `api/app/services/file_validation.py` for the actual cap).
**Expected:** Each rejection shows a clear error toast matching the error code (e.g., `FILE_EMPTY`, `UNSUPPORTED_MIME`, `FILE_TOO_LARGE`).

### 3.4 Document not found
**Steps:** Navigate to `/documents/does-not-exist`.
**Expected:** Friendly 404 state in the UI (not a white screen / stack trace).

---

## 4 — Known gaps / deviations spotted during the review

### 4.1 Frontend role "Consultant" maps to a role the API does not know
**File:** `web/src/lib/api.ts:8`
**Detail:** `ROLE_MAP` includes `'Consultant': 'consultant'`, but `api/config/roles.yaml` defines only `intake_clerk`, `reviewer`, `supervisor`. Selecting "Consultant" in the UI will make every API call return `403 UNKNOWN_ROLE`.
**How to reproduce:** Pick "Consultant" from the role switcher, navigate to `/review`.
**Expected after fix:** Either remove the Consultant entry from `ROLE_MAP` and the role switcher dropdown, or add a `consultant` role (with appropriate actions) to `api/config/roles.yaml`. Decide based on the v1.1.1 spec — a quick grep for `consultant` in `docs/` will tell you if it was meant to exist.

### 4.2 No Playwright / browser E2E suite wired up yet
**File:** `e2e/README.md`
**Detail:** `make test-e2e` fails with "not implemented" because Playwright has not been configured in `e2e/`. This is documented but means we have **zero automated browser coverage**.
**Action:** Manual QA per §2 is the only safety net until Playwright is added. If you have time, a minimal Playwright spec that walks the §2.1 hero flow would be worth its weight in gold.

### 4.3 Response-model shape change (introduced by this fix pass)
**Change:** `POST /documents/{id}/approve-routing`, `/reroute`, `/request-consultation`, `/resolve-consultation`, `/escalate`, `/mark-out-of-scope`, `/close` now return fully-serialized Pydantic DTOs (`WorkflowActionResponse`, etc.) instead of `{}`.
**Risk:** Frontend code that depended on the old (broken) empty-object shape would not have read anything useful anyway, so this is almost certainly a no-op for the UI. But verify during §2.1 that the UI does not throw on the larger payloads.

---

## 5 — Demo scenarios & seed data

### 5.1 Seed scenarios endpoint
```bash
curl -sf $API/api/v1/demo/scenarios | python3 -m json.tool
```
**Expected:** A JSON array (possibly empty until `make seed-demo` has been run; after seed, three entries with titles like "V/v Phê duyệt kế hoạch bảo trì hệ thống IT 2026").

### 5.2 Demo reset
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST $API/api/v1/demo/reset -H 'X-GovDoc-Role: supervisor'
# Expect: 200
curl -s -o /dev/null -w "%{http_code}\n" -X POST $API/api/v1/demo/reset -H 'X-GovDoc-Role: intake_clerk'
# Expect: 403
```
**Pass criteria:** Supervisor can reset; intake_clerk gets 403 FORBIDDEN_ACTION; the document list is empty after reset (ignoring any seed data that reset re-populates).

### 5.3 UI for demo scenarios
Confirm whether the web app exposes a "demo scenarios" picker (look in `DashboardPage.tsx` / `HomePage.tsx`). If it does, verify each seeded scenario can be opened and displays cached AI analyses correctly.

---

## 6 — Evidence panel / retrieval

**Endpoint:** `GET /api/v1/documents/{id}/evidence`
**Backing service:** `RetrievalService` wired in `app.state` with a mock embed function (see `api/app/main.py:48-54`).

### 6.1 Smoke the endpoint
```bash
# After uploading a document (call it $DOC_ID)
curl -sf $API/api/v1/documents/$DOC_ID/evidence -H 'X-GovDoc-Role: reviewer' | python3 -m json.tool
```
**Expected:** `{"document_id": "...", "results": [...]}` — results may be empty if no reference corpus is seeded (likely the case today).

### 6.2 UI
If the document detail page has an "Evidence" tab or panel, click it as **Reviewer** or **Supervisor** and verify:
- Loading state appears, then either results render (with source snippets) or an "empty state" message shows.
- No crash when `results` is `[]`.

### 6.3 Retrieval with live embeddings
The retrieval service is now wired to `RealAIProvider.embed` (`text-embedding-v4`). Semantic search will fire when a non-empty reference corpus is loaded. For an empty corpus (the default out-of-the-box), `/evidence` returns `{"results": []}` which is correct.

---

## 7 — Real Model Studio path (live API — **now the default**)

Live Model Studio is **required** — there is no mock fallback. Credentials are loaded from `.env` (created from `.secrets/*.csv`). The stack refuses to start without them.

### 7.1 Credential probe
```bash
make check-credentials   # runs the `creds` marker tests
```
**Expected:** Each of the 5 locked models (qwen-plus, qwen-max, qwen-vl-plus, text-embedding-v4, qwen3-rerank) returns a 200 within the probe timeout.
**Failure mode:** If any model fails, the probe fails loudly. Fix the credential or model endpoint before continuing.

### 7.2 Live intake with real Qwen
Already verified by Claude during the fix pass:
- Full pipeline (classify → summarize → route → optional escalate) using live Qwen.
- `AIAnalysis.source == "live"` for all rows.
- Vietnamese output is semantically correct (e.g., "UBND" extracted as issuing agency, `phong_hanh_chinh` correctly routed with Vietnamese rationale).

To re-verify independently:
```bash
make test-ai   # runs `live` + `live_integration` markers
```

### 7.3 UI parity check
Upload the same sample via the browser after enabling live mode. Confirm the classification / summary / routing suggestion visible on the detail page matches (or at least is semantically equivalent to) the raw API output.

### 7.4 Evaluation harness
```bash
make eval-ai
```
**Expected:** A JSON/CSV report summarising accuracy across whatever fixtures `scripts/eval_ai_quality.py` uses. Verify the output exists and nothing crashed. This is a weak coverage signal (fixtures are small) but a smoke test.

---

## 8 — OCR / scan path (Qwen-VL) — requires credentials + a scan image

**Backing file:** `api/tests/fixtures/white_10x10.png` is only a placeholder; for a useful scan test, you need a real scanned Vietnamese letter as a PNG or JPEG.

### 8.1 Steps
1. With Model Studio credentials set (see §7.1), upload a scanned document via the UI as **Intake Clerk**.
2. Confirm the extraction method on the detail page reads `qwen-ocr` (not `pypdf` or `plaintext`).
3. Confirm the extracted text contains recognisable Vietnamese.
4. Confirm downstream stages (classify / summarize / route) run successfully on the OCR output.

### 8.2 OCR failure path
1. Upload a deliberately-bad image (e.g., the 10×10 white pixel fixture).
2. **Expected:** The document reaches `ingest_failed` or `extracted` with empty text; the UI should surface a "could not extract text" indicator. It must **not** silently proceed into `analyzed`.

### 8.3 What to log as a bug vs. expected
- "OCR returned gibberish" on a low-quality scan — expected, not a bug.
- "OCR returned empty string and the pipeline still produced a classification" — **bug**, file it.

---

## 9 — Automated smoke scripts (worth running, cheap to do)

### 9.1 `make qa`
Uses the docker network gateway — works in sandboxed environments.
```bash
make qa
```
**Expected:** All seven HTTP checks print OK. Any failure bisects cleanly to the named check.

### 9.2 `make qa-local`
Uses `localhost` — only works if host networking to container ports is open.
```bash
make qa-local
```

### 9.3 Full pytest suite (all markers except live)
Already green, but re-run after any edits:
```bash
make test          # unit + contract + mock_integration
```

### 9.4 Lint + type checks
```bash
make lint
```

---

## 10 — Remote deploy (if demoing on a shared server)

**Not validated by Claude.** If the demo is on a remote box, you must walk through this yourself.

### 10.1 Package
```bash
make remote-package
```
**Expected:** Produces an archive under `.ai/tmp/` or similar; inspect `scripts/remote_package.sh` for the output path.

### 10.2 Deploy
```bash
REMOTE_HOST=user@demo-box make up-remote
```
**Expected:** SSH connection succeeds, stack is brought up on the remote, health endpoints reachable from the demo machine.

### 10.3 Smoke after deploy
From your laptop:
```bash
curl -sf http://demo-box:8000/healthz
curl -s -o /dev/null -w "%{http_code}\n" http://demo-box:3000/
```

---

## 11 — Observability / audit trail

The audit trail is where a demo actually wins or loses — the spec sells "every human + AI action is logged".

### 11.1 Verify audit rows exist
After the §2.1 hero flow:
```bash
curl -sf $API/api/v1/documents/$DOC_ID -H 'X-GovDoc-Role: supervisor' | \
  python3 -c "import sys, json; d=json.load(sys.stdin); \
  [print(e['event_type'], e.get('from_state','-'), '→', e.get('to_state','-')) \
   for e in d['audit_events']]"
```
**Expected:** Events in roughly this order:
- `document.created`
- `extraction.completed`
- `ai.call` × 3 (classify / summarize / route)
- `workflow.transition` routed → under_review
- `workflow.transition` under_review → in_consultation
- `workflow.transition` in_consultation → under_review
- `workflow.transition` under_review → approved
- `workflow.transition` approved → closed

### 11.2 Prompt version audit
```bash
curl -sf $API/api/v1/meta/prompt-versions | python3 -m json.tool
```
**Expected:** Three rows (classify / summarize / route) each with a 12-char hex `id`, `file_path`, and `label` (if labels were configured in `api/config/prompt_versions.yaml`).
**Also verify:** On the document detail response, each `analyses[*].prompt_version` matches one of these hashes (not `"unknown"`). This is the fix from §0 — regression-test it explicitly.

### 11.3 UI surface
If the UI has an "Audit" or "History" tab on the document detail, verify it renders the chain in chronological order with clear labels.

---

## 12 — Priority ranking for a time-boxed QA pass

If you only have an hour, do these in this order:

1. **§2.1 Web UI hero flow** (biggest risk, highest demo value) — 20 min
2. **§4.1 Consultant-role bug** (verify whether it blocks the demo) — 5 min
3. **§11 Audit trail** (easy win, sells the demo story) — 10 min
4. **§5 Demo scenarios** (if you plan to showcase seeded cases) — 10 min
5. **§3.1–3.3 Error paths** (quick sanity checks) — 10 min
6. **§7 Live Model Studio** (now the default; credentials pre-loaded in `.env`) — already verified, re-run `make test-ai` if needed

Skip §8 OCR, §10 remote deploy, and §6 evidence panel unless the demo narrative specifically features them.

---

## 13 — Reporting template

When you run QA, record findings in the same `docs/qa-report/` directory with filename `YYYY-MM-DD_qa_run_<initials>.md`. Minimum fields:

```
## Run summary
- Date / tester / stack hash (`git rev-parse HEAD`)
- Env: local / remote / sandbox
- Credentials used: mock-only / live

## Results
| Section | Result | Notes |
|---|---|---|
| §2.1 Hero UI | pass/fail/partial | |
| §3 Edge cases | | |
| §4.1 Consultant bug | confirmed/not-applicable | |
| §5 Demo scenarios | | |
| §6 Evidence panel | | |
| §7 Live Model Studio | skipped/pass/fail | |
| §8 OCR | skipped/pass/fail | |
| §11 Audit trail | | |

## Bugs found
- [link to issue or inline description]

## Recommendation
- ready to demo / needs fixes / blocked on <x>
```

---

## Appendix A — File references used in this plan

- State machine: `api/app/services/workflow.py`
- Workflow endpoints: `api/app/api/v1/endpoints/review.py`
- Document endpoints: `api/app/api/v1/endpoints/documents.py`
- Intake service: `api/app/services/intake_service.py`
- Analysis orchestrator: `api/app/services/ai/analysis_service.py`
- Prompt registry: `api/app/services/prompt_registry.py`
- Frontend role mapping: `web/src/lib/api.ts`
- Nginx proxy: `web/nginx.conf`
- Demo seed: `api/app/services/demo.py`, `scripts/seed_demo_data.py`
- Local QA smoke: `scripts/qa_local.sh`
- Wait-for-healthy: `scripts/wait_for_compose_healthy.sh`
- Spec sources: `docs/govdoc_implementation_plan.md`, `docs/govdoc_test_plan.md`, `docs/govdoc_source_of_truth_plan_v1_1.md`

## Appendix B — Fixes applied in this pass (for full provenance)

| File | Change | Why |
|---|---|---|
| `api/app/services/workflow.py` | Added `under_review → approved` and `in_consultation → approved` | `/close` was unreachable before |
| `api/app/api/v1/endpoints/documents.py` | Implicit `routed → under_review` on reviewer/supervisor GET | Per spec §3.4: "reviewer opens record (implicit on read)" |
| `api/app/api/v1/endpoints/documents.py` + `api/app/services/intake_service.py` | Thread `request.app.state.prompt_registry` into intake + re_analyze | Live intake was stamping `"unknown"` prompt_version |
| `api/app/services/ai/analysis_service.py` | Per-stage idempotency (check each stage's current prompt_version) | Old all-or-nothing check gated on classify's version |
| `api/app/api/v1/endpoints/review.py` + `api/app/schemas/document.py` | Added `response_model` on all workflow endpoints; introduced `WorkflowActionResponse` / `RoutingActionResponse` / `ConsultationActionResponse` | Endpoints were returning `{}` due to missing response_model on ORM returns |
| `api/app/services/ai/mock_provider.py`, `.../extraction/mock_provider.py`, `.../retrieval/mock_provider.py` | **Deleted** | No fallback — real provider is mandatory |
| `api/app/api/deps.py` | `get_ai_provider()` returns `RealAIProvider()` unconditionally; removed `get_extraction_provider` / `get_retrieval_provider` stubs | Fail fast per CLAUDE.md |
| `api/app/api/v1/endpoints/documents.py` | Removed `_get_ai_provider()` with silent except; AI provider now via `Depends(deps.get_ai_provider)` | Allows test DI override without production fallback |
| `api/app/main.py` | `settings.validate_ai_config()` at lifespan startup; retrieval wired to `RealAIProvider().embed` | Fail fast; live `text-embedding-v4` for semantic search |
| `docker-compose.yml` | `env_file: .env`; removed `MODELSTUDIO_*=${...:-}` placeholders | Credentials flow from `.env` into container |
| `.env` | Created from `.secrets/*.csv` with live Model Studio credentials | Gitignored; source of truth for local + docker dev |
| `api/tests/conftest.py` + `api/tests/fixtures/fake_ai_provider.py` | Test-scoped `FakeAIProvider`; autouse fixture overrides `get_ai_provider` dep + stubs lifespan | Tests run offline without hitting Model Studio |
