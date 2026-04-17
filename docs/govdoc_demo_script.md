# GovDoc SecureFlow — Detailed Demo Script

Version: 1.0  
Status: Demo runbook  
Audience: presenter, operator, backup operator  
Paired artifacts:
- `govdoc_source_of_truth_plan_v1_1.md`
- `govdoc_implementation_plan.md`
- `govdoc_test_plan.md`

---

## 1) Demo objective

Show a credible, end-to-end MVP for the selected public-sector use-case:

> AI-assisted intake and triage of incoming official administrative documents for a ministry / provincial office records desk.

The demo must prove, in a short time, that GovDoc SecureFlow can:

- intake a real document
- extract text from born-digital or scan-like input
- classify the document
- summarize it
- suggest the right department
- let a human approve/correct it
- handle ambiguity honestly
- support consultation and tracked workflow progression
- show role-based visibility without real login
- clearly use Alibaba Model Studio / Qwen in the core flow

---

## 2) Recommended demo length

### Main demo
**6–8 minutes**

### Backup compressed version
**3–4 minutes**

### Expanded Q&A version
**10–12 minutes**

---

## 3) Demo strategy

The demo should not try to show “everything”.

It should show **3 tightly chosen flows**:

1. **Hero flow**
   - normal incoming document
   - clear routing suggestion
   - human approval
   - consultation
   - tracked progression
   - closeout

2. **Ambiguity flow**
   - multi-department document
   - lower confidence
   - consultation / supervisor review suggested

3. **Scan robustness flow**
   - low-quality scan
   - OCR path visible
   - still usable

Do **not** spend time on:
- broad platform claims
- admin/config screens unless asked
- technical implementation details too early
- fake-perfect outputs

---

## 4) Presenter roles

### 4.1 Suggested team roles during demo

#### Presenter
Talks through the product and value.

#### Operator
Clicks through the UI and switches roles/scenarios.

#### Backup operator
Keeps local fallback open and watches logs/health.

If solo:
- keep both the “talk track” and “click path” visible in notes
- use seeded demo mode for stability

---

## 5) Demo prerequisites

Before the live demo, verify:

- app is already running
- seeded demo data loaded
- `make check-credentials` passed
- hero scenario works end-to-end locally
- scan scenario works locally
- ambiguity scenario works locally
- reference/evidence panel is populated
- role switcher works
- remote/local health is green
- one fallback browser tab is ready
- one API health/log tab is ready but hidden

### 5.1 Browser prep
Open these in advance:
- main app
- backup tab at dashboard/home
- hidden tab with health/log view
- hidden tab with seeded scenario list if available

### 5.2 Recommended presentation mode
- use fullscreen browser
- zoom UI if needed
- keep cursor deliberate
- avoid typing long text live if possible

---

## 6) Demo data to use

Use seeded scenario names that are easy to say out loud.

Recommended labels:

- `hero_incoming_cong_van`
- `ambiguous_multi_department`
- `scan_low_quality_notice`
- `out_of_scope_negative`

If current app uses different names, map them clearly in advance.

---

## 7) Demo screen map

The demo should use these screens in this order:

1. **Demo home / role switcher**
2. **Intake queue**
3. **Record detail / AI analysis**
4. **Review / routing approval**
5. **Consultation thread**
6. **Tracking dashboard**
7. **Response / closeout**

---

## 8) Main presenter framing (opening lines)

### Opening option A — concise
“GovDoc SecureFlow helps a public-sector intake desk process incoming official documents faster and more safely. Instead of manually reading every PDF or scan, the system extracts, classifies, summarizes, suggests routing, and keeps a visible audit trail with human approval.”

### Opening option B — more problem-led
“In many public-sector workflows, incoming documents are still manually read, classified, forwarded, and tracked. That creates delays, misrouting, and poor visibility. GovDoc SecureFlow is our AI-assisted intake and triage workflow for that exact problem.”

### Opening option C — Alibaba-led
“We built GovDoc SecureFlow on Alibaba Model Studio. Qwen handles classification, summarization, routing suggestions, and OCR fallback, while the app keeps the workflow, auditability, and human review deterministic.”

---

## 9) Detailed hero demo script

---

## Scene 0 — Demo home / role switcher

### Goal
Set the context fast.

### What the operator does
- open the app home/dashboard
- show role switcher
- keep default role as **Intake Clerk**
- point to available seeded scenarios / queue counts

### What the presenter says
“This is the intake-facing view. We intentionally do not use real login in the MVP; instead, we simulate operational roles so we can show role-based visibility and actions clearly during the demo.”

### What to point at
- role switcher
- queue summary
- seeded scenarios
- status counts

### Important visual proof
The audience should immediately see:
- this is not a chatbot
- this is a workflow app
- roles exist
- records exist

### Time
**20–30 seconds**

---

## Scene 1 — Intake queue

### Goal
Show a new incoming document entering the system.

### What the operator does
Option A:
- upload the seeded hero document live

Option B:
- open a pre-seeded hero document in the intake queue and mention it was uploaded moments earlier

Preferred:
- upload live if stable
- use seeded record if live upload adds risk

### What the presenter says
“Here a clerk receives an incoming official document. The system stores the original file, extracts content, and creates a tracked record instead of leaving the document in a mailbox or a chat thread.”

### What to point at
- filename
- intake timestamp
- initial security level
- ingest status
- file preview/source file info

### If uploading live
Say:
“I’m uploading a real sample administrative document from our dataset.”

### Time
**30–45 seconds**

---

## Scene 2 — Record detail / AI analysis

### Goal
Show the core AI value.

### What the operator does
- open the newly analyzed hero record
- let the analysis results appear
- scroll only enough to show:
  - extracted text preview
  - classified type
  - summary
  - suggested department
  - confidence
  - rationale
  - evidence panel

### What the presenter says
“After intake, the system creates a normalized artifact from the original file. Then Qwen classifies the document type, summarizes it, suggests the receiving department, and gives a confidence score and rationale.”

### What to explicitly mention
- original file is preserved
- extracted text is separate from original
- AI recommends but does not auto-finalize the workflow
- the output is structured, not just free text

### Suggested talk track
“In this example, the system has identified the document as a công văn, summarized the key intent, and suggested the most likely receiving department. We also keep the rationale and confidence visible so the clerk can decide whether to trust it or override it.”

### What to point at
- document type
- summary
- department suggestion
- confidence
- evidence panel / similar references
- prompt/model metadata if visible

### Time
**60–90 seconds**

---

## Scene 3 — Review / routing approval

### Goal
Show the human-in-the-loop step.

### What the operator does
- stay as **Intake Clerk**
- review the routing suggestion
- approve it
- or make one small controlled edit if the demo scenario is designed for that

Preferred:
- approve the hero record quickly
- do not make the hero flow look uncertain unless necessary

### What the presenter says
“This is a key design decision: the AI never silently finalizes state. It recommends, and the clerk approves or corrects it. That makes the system useful without pretending to be fully autonomous.”

### If using a small correction
Say:
“The clerk can also correct category or routing before assignment. Every such change is logged.”

### What to point at
- approve action
- optional reroute/change-category action
- audit/event update after approval

### Time
**30–45 seconds**

---

## Scene 4 — Role switch to Department Reviewer

### Goal
Show role-based progression.

### What the operator does
- switch role to **Department Reviewer**
- reopen the same record
- show that the record is now assigned and visible in reviewer context

### What the presenter says
“Now I’m switching from intake to the receiving department. The same record moves forward in the workflow, but the available actions and visible context change with role.”

### What to point at
- role switcher
- changed action buttons
- assigned department / owner state
- state timeline

### Time
**20–30 seconds**

---

## Scene 5 — Consultation thread

### Goal
Show cross-department collaboration, not just one-step routing.

### What the operator does
- request consultation from another department
- open the consultation thread
- if seeded response exists, show it
- if not, use a seeded consultation note already attached

### What the presenter says
“Many public-sector cases are not solved by one perfect first assignment. Some documents need consultation across departments. So the system doesn’t hide uncertainty; it supports a controlled collaboration path.”

### Suggested talking line
“Instead of the document disappearing into email or chat, the consultation becomes part of the record’s visible timeline.”

### What to point at
- requested department
- reason for consultation
- response note
- timeline update
- audit trail

### Time
**45–60 seconds**

---

## Scene 6 — Supervisor view / Tracking dashboard

### Goal
Show status visibility and operational control.

### What the operator does
- switch role to **Supervisor**
- open dashboard / tracking view
- show the same record’s progression across states
- show queue/state summaries if available

### What the presenter says
“Supervisors need visibility more than raw document text. Here the same case is visible as a workflow object: where it entered, who touched it, what the AI suggested, what humans approved, and where it is now.”

### What to point at
- timeline
- current owner
- state counts
- pending items
- audit summary

### Time
**30–45 seconds**

---

## Scene 7 — Response / closeout

### Goal
Complete the end-to-end story.

### What the operator does
- open response/disposition view
- show prepared disposition / closeout state
- close the case or show it ready to close

### What the presenter says
“The point of the system is not just to classify PDFs. It is to move a real document through a real workflow toward a tracked resolution.”

### What to point at
- response or disposition note
- closure state
- final owner
- final audit entry

### Time
**20–30 seconds**

---

## 10) Ambiguity demo script

### Goal
Prove the system is honest when unsure.

### When to use
- immediately after hero flow
- or during Q&A if judges ask about edge cases

### What the operator does
- switch to seeded scenario `ambiguous_multi_department`
- open record detail
- show:
  - lower confidence
  - secondary department suggestion
  - consultation recommendation or supervisor-review flag

### What the presenter says
“This document is intentionally harder. Here the system does not pretend to have one perfect answer. Instead, it lowers confidence, surfaces ambiguity, and recommends consultation or escalation.”

### Key message
**Honest uncertainty is a feature**, not a weakness.

### What to point at
- lower confidence
- secondary department
- needs consultation / needs supervisor review
- rationale text
- evidence panel

### Time
**45–60 seconds**

### One-line close
“So the app is not overfit to easy cases only.”

---

## 11) Scan robustness demo script

### Goal
Show OCR path and robustness for messy input.

### What the operator does
- open seeded scenario `scan_low_quality_notice`
- show extraction method = OCR / scan path
- show extracted text preview and resulting classification/summary

### What the presenter says
“Public-sector intake is rarely clean digital text only. So we also support scan-like inputs. In this scenario, the system uses the OCR path, still extracts enough signal, and continues through the same workflow.”

### What to point at
- file preview / scan appearance
- extraction method
- OCR warnings if any
- still-usable summary and routing output

### Important message
Do **not** oversell.
Say:
“This is good enough for triage and review, not a claim of perfect OCR.”

### Time
**45–60 seconds**

---

## 12) Out-of-scope / failure honesty script

### Goal
Be ready if someone asks what happens when the AI is wrong or input is not suitable.

### Recommended answer
“We explicitly avoid fake certainty. If the system is unsure, it lowers confidence and asks for human confirmation. If a file is unsupported or extraction fails, that error is surfaced instead of hidden.”

### Optional UI proof
- open out-of-scope scenario
- show out-of-scope label or review action
- or show explicit error state from a known test fixture if safe

### Time
**20–30 seconds**

---

## 13) Suggested narrative flow by minute

### Minute 0–1
- problem framing
- role switcher
- intake screen

### Minute 1–3
- hero document analysis
- classification
- summary
- routing
- rationale

### Minute 3–4
- human approval
- role switch to reviewer
- consultation

### Minute 4–5
- supervisor/tracking dashboard
- closeout

### Minute 5–6
- ambiguity case

### Minute 6–7
- scan/OCR case

### Minute 7–8
- close with value statement + Alibaba/Qwen mention

---

## 14) Strong closing lines

### Closing option A
“GovDoc SecureFlow turns incoming administrative documents from unstructured files into tracked workflow objects, with Qwen handling understanding and the application enforcing human review and auditability.”

### Closing option B
“Our goal was not to build a generic chatbot for government. It was to build a realistic intake and triage workflow that public-sector teams could actually recognize and use.”

### Closing option C
“The key value is not only AI extraction. It is the combination of classification, routing, human review, and visibility in one operational flow.”

---

## 15) What to say if asked about Alibaba usage

### Short answer
“We use Alibaba Model Studio as the core AI layer. Qwen handles classification, summarization, routing suggestions, ambiguity handling, and OCR fallback for scan-like inputs.”

### Slightly longer answer
“The application logic remains deterministic around workflow, permissions, and auditability. Qwen provides understanding and recommendations; the app decides and records state.”

---

## 16) What to say if asked why no login

### Recommended answer
“For the MVP, we intentionally skipped real auth to focus on the core workflow. But we still simulate operational roles, and backend permissions are enforced around those simulated roles.”

---

## 17) What to say if asked whether it is overfit to one case

### Recommended answer
“We demo one concrete workflow to keep the MVP credible, but the taxonomy, departments, prompts, and thresholds are structured so the same engine can be adapted to similar public-sector intake workflows.”

---

## 18) Operator click checklist

### Before speaking
- [ ] app loaded
- [ ] role = Intake Clerk
- [ ] hero scenario ready
- [ ] main record page pre-warmed if needed

### During hero flow
- [ ] upload/open hero record
- [ ] show detail page
- [ ] show summary/routing/confidence
- [ ] approve
- [ ] switch reviewer
- [ ] consultation
- [ ] switch supervisor
- [ ] show timeline
- [ ] closeout

### During edge-case section
- [ ] open ambiguity scenario
- [ ] show lower confidence
- [ ] open scan scenario
- [ ] show OCR path

---

## 19) Backup plan if live inference is slow

If live inference lags:

1. say:
   “We also prepared seeded replay so the workflow remains stable for demo conditions.”
2. switch to cached/seeded scenario view
3. continue with the same product narrative
4. do not pretend it is live if it is cached

### Required honesty line
“This particular scenario is pre-seeded for demo stability, but the same workflow is backed by the live pipeline.”

---

## 20) Backup plan if one screen fails

### If upload fails
- use pre-seeded hero record

### If consultation thread breaks
- show seeded consultation response already on the record

### If dashboard fails
- stay in record timeline view and narrate the same lifecycle

### If OCR fails
- open a previously processed scan scenario instead

---

## 21) Things to avoid saying

Do not say:
- “It works perfectly”
- “The AI always knows the correct department”
- “This replaces human review”
- “This is production-secure already”
- “It can handle all public-sector documents”
- “This is a full DMS replacement”

Prefer:
- “AI-assisted”
- “triage”
- “human approval”
- “confidence and rationale”
- “auditability”
- “visible workflow”

---

## 22) Demo success criteria

The demo is successful if the audience clearly understands that:

1. the problem is real and specific
2. this is a workflow product, not a chatbot wrapper
3. Alibaba/Qwen is central to the value
4. the system handles both normal and hard cases
5. humans stay in control
6. the workflow is visible and tracked
7. the MVP is credible, not over-claimed

---

## 23) Ultra-short 3-minute version

If time is cut, do this:

1. open home / role switcher
2. open pre-seeded hero record
3. show:
   - type
   - summary
   - routing
   - confidence
4. approve routing
5. switch reviewer
6. show consultation
7. switch supervisor
8. show tracking timeline
9. open one ambiguous or scan case
10. close with Alibaba/Qwen explanation

### Suggested short closing
“We built a public-sector intake and triage workflow where Qwen handles understanding and the app handles control, review, and tracking.”

---

## 24) Presenter rehearsal checklist

Before final event rehearsal:
- [ ] run full demo twice without narration
- [ ] run full demo once with narration
- [ ] run compressed 3-minute version once
- [ ] test role switches
- [ ] test seeded fallback
- [ ] test scan scenario
- [ ] verify confidence/ambiguity case still behaves as expected
- [ ] verify logs/health hidden tab works
- [ ] verify remote host reachable if using remote deployment

---

## 25) Final presenter reminder

The strongest version of this demo is:

- calm
- concrete
- workflow-first
- honest about uncertainty
- explicit about AI usage
- explicit about human control

Do not race.
Do not oversell.
Show one real workflow well.
