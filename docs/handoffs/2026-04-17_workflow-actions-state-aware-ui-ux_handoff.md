# GovDoc SecureFlow — Workflow Actions State-Aware Fix Handoff

Status: Implementation handoff note
Date: 2026-04-17
Scope: Document detail page `Workflow actions` behavior and UX on the deployed app

## 1) Problem statement

On the document detail page, the `Workflow actions` buttons are wired to real backend endpoints, but several buttons are still presented as available even when the current document is already in a terminal or otherwise incompatible workflow state.

Example observed on the remote deployment:

- URL: `http://47.84.131.45:3000/documents/eab25250-95f2-41ad-b61b-e956246d2638`
- Document status: `closed`
- Current behavior:
  - some actions are correctly disabled because the page checks document status
  - other actions remain clickable even though the backend should reject them

This creates three problems:

- poor demo quality: the UI looks unfinished because it invites actions that immediately fail
- weak workflow clarity: the user cannot tell which actions are actually legal at the current state
- avoidable API noise: invalid requests are sent for transitions that should have been blocked earlier in the UI

The next session should fix both correctness and UX, not just disable a couple of buttons.

## 2) Confirmed current-state findings

### Frontend wiring is real

The buttons on the document detail page call real API endpoints through `handleAction()` in:

- `web/src/pages/DocumentDetailPage.tsx`

Current action mapping includes:

- `approve-routing`
- `reroute`
- `request-consultation`
- `resolve-consultation`
- `escalate`
- `mark-out-of-scope`
- `close`
- `analyze`

### Backend endpoints are real

The API routes exist in:

- `api/app/api/v1/endpoints/review.py`

and are not placeholders.

### Current UX gap

For the remote `closed` demo document, these actions should not appear actionable:

- `Escalate to supervisor`
- `Mark out of scope`
- `Close document`

Even if the backend rejects the request, the UI should not advertise these as valid next steps.

## 3) Desired end state

The `Workflow actions` panel should become a state-aware action surface that is:

- correct with respect to the current workflow state
- consistent with role-based permissions
- explicit about why an action is unavailable
- clean for demos and realistic for real operators

The user should be able to open any document and immediately understand:

- what the current workflow state is
- which actions are available now
- which actions are unavailable and why
- when no further actions are possible because the document is terminal

## 4) Required design direction

Do not stop at “disable the wrong buttons.”

The panel should be improved so that:

- valid actions are visually primary and easy to identify
- invalid actions are either hidden or shown as disabled with a clear reason
- terminal-state documents have a concise read-only treatment
- action grouping feels intentional rather than a flat stack of generic buttons

Recommended UX direction:

- Add a small status-aware header or helper text above the action list, such as:
  - `Available actions for this document`
  - `No further workflow actions are available because this document is closed`
- Group actions into meaningful sections if helpful:
  - `Analysis`
  - `Review`
  - `Consultation`
  - `Closeout`
- Prefer hiding impossible actions for terminal states if the panel becomes too noisy.
- If disabled actions remain visible, they must show an explicit reason, for example:
  - `Only available while the document is under review`
  - `This document is already closed`
  - `No unresolved consultation notes remain`

The final UI should look deliberate, not merely defensive.

## 5) Implementation passes

This work should be executed in multiple passes. Do not collapse them into one unstructured edit cycle.

### Pass 1 — Baseline audit and rule inventory

Goal:
- Build an explicit frontend action-availability matrix from real backend workflow rules and real role permissions.

Required work:

- Read current workflow transition logic in:
  - `api/app/services/workflow.py`
  - `api/app/api/v1/endpoints/review.py`
  - `api/app/api/v1/endpoints/documents.py`
- Read current role/action permissions exposed by:
  - `api/app/api/v1/endpoints/meta.py`
  - any role helper used by the frontend
- Inventory every action shown in `Workflow actions` and determine:
  - allowed roles
  - allowed statuses
  - required extra conditions
  - expected terminal-state behavior

Deliverable:

- A small in-code or note-level matrix that is explicit enough to drive implementation without ambiguity.

Pass 1 acceptance criteria:

- Every visible button in `Workflow actions` has an explicit rule definition.
- The rule definition covers both role gating and state gating.
- Any mismatch between backend legality and frontend presentation is documented before code changes begin.

### Pass 2 — Introduce a state-aware action model in the frontend

Goal:
- Replace ad hoc inline button conditions with a single source of truth for action availability on the document detail page.

Required work:

- Refactor `web/src/pages/DocumentDetailPage.tsx` so button rendering is driven by a computed action model.
- Each action model entry should include at least:
  - action id
  - label
  - allowed roles
  - availability predicate
  - disabled reason or hidden-state reason
  - visual grouping or priority
- Avoid scattering status checks across JSX.
- Keep the model readable enough to review without running the app.

Recommended implementation shape:

- Introduce a helper such as:
  - `getWorkflowActions(doc, role)`
  - or a local `const workflowActions = [...]` with computed availability
- Centralize status checks in helper functions, for example:
  - `canAnalyze(doc, role)`
  - `canApproveRouting(doc, role)`
  - `canRequestConsultation(doc, role)`
  - `canResolveConsultation(doc, role)`
  - `canEscalate(doc, role)`
  - `canMarkOutOfScope(doc, role)`
  - `canClose(doc, role)`

Pass 2 acceptance criteria:

- No button is rendered as active unless it is actually intended to be actionable in the current document state.
- Terminal-state documents no longer show misleading active actions.
- The action gating logic is centralized and reviewable.

### Pass 3 — UX upgrade for the action panel

Goal:
- Make the panel clearer and more professional after correctness is fixed.

Required work:

- Improve the visual hierarchy of the `Workflow actions` section.
- Add contextual helper text that reflects the current document status.
- Decide action-by-action whether unavailable actions should be:
  - hidden
  - disabled with explanation
  - replaced by a terminal-state message
- Ensure the panel reads well on both:
  - active in-flight documents
  - closed/out-of-scope documents
- Ensure button variants communicate intent clearly:
  - neutral action
  - caution/destructive action
  - terminal/closeout action

Recommended UX expectations:

- `closed` document:
  - no misleading active escalation/out-of-scope/close buttons
  - either a compact terminal-state message or a minimal disabled action presentation
- `in_consultation` document:
  - consultation-related actions are visually emphasized
  - unavailable closeout actions are not presented as primary next steps
- `analyzed` document:
  - `Approve routing` stands out as the obvious next action for reviewer/supervisor

Pass 3 acceptance criteria:

- The panel clearly communicates next valid steps without trial-and-error clicking.
- Invalid actions do not compete visually with valid ones.
- Terminal states have an intentional read-only UX.

### Pass 4 — Backend consistency review and targeted fixes

Goal:
- Ensure the backend behavior matches the frontend’s new expectations.

Required work:

- Re-check that every workflow endpoint enforces its own transition legality.
- Confirm there are no remaining endpoints that allow illegal transitions solely because the UI stopped exposing them.
- Add or tighten backend validation if any inconsistencies remain.

Specific items to re-check:

- `approve-routing`
- `reroute`
- `request-consultation`
- `resolve-consultation`
- `escalate`
- `mark-out-of-scope`
- `close`
- `analyze`

Important note:

- `mark-out-of-scope` was already fixed in local code to validate workflow transitions.
- Do not assume the rest are equally safe without re-checking them.

Pass 4 acceptance criteria:

- Backend rejects illegal transitions consistently for all workflow actions.
- Frontend and backend no longer disagree about what is meant to be actionable.
- There is no endpoint whose invalid usage is only prevented by the UI.

### Pass 5 — Unit tests and targeted behavior tests

Goal:
- Lock the new action rules and UX behavior so they do not regress.

Required work:

- Add frontend tests if the repo already has an appropriate pattern for component or logic testing.
- If direct component tests are too heavy, extract pure action-gating helpers and unit-test them.
- Add backend tests for any endpoint behavior changed in Pass 4.

Minimum recommended test coverage:

- frontend action model tests:
  - `closed` document -> no active `close`, `escalate`, or `mark out of scope`
  - `analyzed` document for reviewer -> `approve routing` available
  - `in_consultation` document with unresolved note -> `resolve consultation` available
  - `in_consultation` document with no unresolved note -> `resolve consultation` unavailable with clear reason
  - `under_review` document -> `request consultation` available
- backend tests:
  - invalid transitions return `400 INVALID_TRANSITION`
  - legal transitions still succeed

Suggested file targets:

- frontend:
  - new extracted helper test near `web/src/pages/DocumentDetailPage.tsx`
  - or `web/src/lib/` / `web/src/features/` if the repo has a better fit
- backend:
  - review endpoint tests under existing API test structure

Pass 5 acceptance criteria:

- New tests fail before the fix and pass after the fix.
- Action availability for the key statuses is covered by automated tests.
- Backend invalid-transition behavior is covered for any changed endpoint.

### Pass 6 — Local redeploy and real verification

Goal:
- Prove the fixes work in the running app, not just in isolated code/tests.

Required work:

- Run `make ci`
- Run `make up`
- If demo data has drifted, reseed in the supported way already used in this repo
- Verify locally in the browser against the deployed app

Required verification scenarios:

1. Closed document
- Open a known `closed` demo document detail page.
- Confirm the action panel does not present misleading active actions.
- Confirm the terminal-state UX is clear.

2. Under-review or analyzed document
- Open a document where routing/review actions are genuinely available.
- Confirm the correct next action is visually obvious.

3. In-consultation document
- Open a document in consultation.
- Confirm consultation-specific controls and messaging are correct.

4. Failure-path verification
- Attempt at least one invalid backend action directly through HTTP or existing test tooling.
- Confirm the API still rejects it cleanly.

Pass 6 acceptance criteria:

- `make ci` passes.
- `make up` succeeds.
- Local browser verification confirms the new button behavior and improved UX.
- No new runtime errors are introduced on the document detail page.

## 6) Suggested implementation details

These are recommendations, not hard requirements, but they should improve maintainability.

### Frontend structure

Prefer extracting action-rule logic out of the JSX body.

Example direction:

- `web/src/pages/document-detail/workflow-actions.ts`
- `web/src/pages/document-detail/workflow-actions.test.ts`

Potential exported helpers:

- `getWorkflowActionStates(doc, role)`
- `isTerminalStatus(status)`
- `getActionAvailabilityReason(action, doc, role)`

This will make the logic testable without mounting the whole page.

### UX details

Suggested UX behaviors:

- hide actions that are impossible and unhelpful in the current state
- disable actions that are conceptually relevant but currently blocked, with a reason
- show a compact informational block when there are no workflow actions available

Suggested language examples:

- `This document is closed. No further workflow actions are available.`
- `Consultation can only be requested while the document is under review.`
- `No unresolved consultation notes remain.`

### Backend review

If any backend endpoint currently lacks `validate_transition()`, add it unless there is a defensible reason not to.

Also verify whether:

- `escalate` should remain audit-only
- or should transition into a distinct state

If the product intentionally treats `escalate` as an audit event rather than a state change, the UI wording should reflect that more clearly.

## 7) Files likely to be touched

Expected primary files:

- `web/src/pages/DocumentDetailPage.tsx`
- `api/app/api/v1/endpoints/review.py`

Possible new files:

- `web/src/pages/document-detail/workflow-actions.ts`
- `web/src/pages/document-detail/workflow-actions.test.ts`

Possible related files:

- `api/app/services/workflow.py`
- backend test files covering workflow endpoints
- frontend shared UI components if button treatment is generalized

## 8) Risks and review traps

The next session should avoid these mistakes:

- fixing only the three visibly bad buttons and leaving the action logic fragmented
- hiding everything instead of designing a clearer terminal-state UX
- relying on the frontend only, without verifying backend transition enforcement
- skipping tests because the behavior “looks right” manually
- verifying only with one document status

## 9) Overall acceptance criteria

This handoff is complete only when all of the following are true:

- The `Workflow actions` panel on document detail pages is driven by centralized, explicit action-availability rules.
- The UI no longer presents invalid workflow actions as active for terminal or incompatible states.
- The UX clearly communicates what actions are available now and why others are unavailable.
- Terminal-state documents have an intentional read-only action experience.
- Backend endpoints consistently reject illegal transitions.
- Automated tests cover the key action-state rules and any changed backend behavior.
- `make ci` passes.
- `make up` succeeds.
- Local browser verification confirms the fixes on at least:
  - one `closed` document
  - one `analyzed` or `under_review` document
  - one `in_consultation` document

## 10) Suggested execution order for the next session

Use this order to keep the work controlled:

1. Audit workflow/state rules and define the action matrix.
2. Refactor frontend action gating into a central helper/model.
3. Improve the action-panel UX and terminal-state treatment.
4. Re-check backend transition enforcement and patch any gaps.
5. Add frontend and backend tests.
6. Run `make ci`.
7. Run `make up`.
8. Verify the real app locally in the browser.

## 11) Exit checklist for the next session

Before closing the next session, confirm all of these explicitly:

- action matrix implemented
- invalid active buttons removed or intentionally disabled with reasons
- terminal-state UX improved
- tests added and passing
- `make ci` passing
- `make up` passing
- local browser verification completed
- final note includes what changed, how it was validated, and any remaining risks
