# GovDoc SecureFlow — Source of Truth Plan for Public Sector Track

Version: 1.1  
Status: Working source of truth for scoping, baseline generation, and downstream handoff plans  
Owner: User / project lead  
Intended readers: product lead, baseline builder, coding agents, QA agents, demo/pitch prep

---

## 1) Purpose of this document

This note freezes the **target use-case**, **MVP scope**, **Alibaba Cloud stack choices**, **data-pack decisions**, **role simulation approach**, **UI scene map expectations**, and **non-goals** for the GovDoc SecureFlow hackathon project.

This is **not** the implementation plan and **not** the test plan.

This file should be treated as the **source of truth** used to generate, later:

- implementation plan
- test plan
- AI quality evaluation plan
- demo / pitch plan
- seeded scenario list
- baseline-app spec for Google AI Studio
- coding-agent handoff notes

---

## 2) Hackathon optimization goals

The project must optimize for the judging behavior implied by the event rules, notes, and public-sector brief:

1. **Problem relevance must be obvious quickly**
   - The judge should understand the pain in under 30 seconds.
   - The project must directly match the public-sector track, not look like a generic OCR/chatbot demo.

2. **End-to-end workflow matters more than raw AI cleverness**
   - The strongest MVP should demonstrate the flow of:
     - classification
     - department matching / routing
     - summarization
   - The demo should show that these three happen inside one realistic administrative workflow.

3. **Alibaba / Qwen usage must be explicit**
   - The judges must be able to see exactly where Alibaba Cloud is used.
   - “We used Qwen” is not enough.
   - Each step should show which model/API is used and why.

4. **Execution quality beats over-scope**
   - A smaller but polished system is better than a broad, unfinished “public-sector platform”.
   - The MVP should choose one concrete workflow and do it well.

5. **Pitch clarity matters**
   - The system should be easy to explain as:
     - input
     - processing
     - human review
     - tracked outcome
   - The live demo should map directly to the public-sector brief’s workflow.

---

## 3) Selected target use-case

### 3.1 Chosen use-case

**AI-assisted intake and triage of incoming official administrative documents (`văn bản đến`) for a ministry / provincial office records desk (`văn thư / lưu trữ / văn phòng HĐND-UBND`).**

### 3.2 In plain words

The app helps a records / intake clerk receive incoming official documents, register them, classify them, summarize them, suggest the correct receiving department, and track the document through the early part of the public-sector workflow with human review and auditability.

### 3.3 Why this use-case was selected

This use-case is the best fit because it aligns closely with the public-sector brief:

- intake of physical + digital documents
- manual classification and routing delays
- fragmented cross-department handoffs
- repeated review / consultation
- need for visibility and tracking
- strict confidentiality / access control

It also maps naturally to the track’s canonical workflow:

`intake → registration → distribution → review → consultation → response`

### 3.4 Why this use-case is better than other public data options

#### Better than “court judgment analysis” as the hero use-case
- Court judgments are useful as optional reference / hard retrieval material.
- But the public-sector track is about **administrative document processing** across organizations, not about legal research alone.
- Court documents are therefore secondary, not primary.

#### Better than “generic government AI assistant”
- Too broad
- Too hard to demonstrate convincingly
- Easier for judges to dismiss as a chatbot wrapper

#### Better than “full enterprise/government DMS replacement”
- Too large for a hackathon
- Too much scope in auth, permission admin, templates, search, archival compliance, etc.
- Does not optimize for live demo clarity

---

## 4) Product statement

### 4.1 One-sentence statement

GovDoc SecureFlow is a secure AI-assisted intake and triage system for incoming administrative documents that classifies, summarizes, routes, and tracks records across departments with human approval and auditability.

### 4.2 User-facing statement

Instead of staff manually reading every incoming PDF or scan, deciding the type, guessing the target department, and passing it around by phone/email/chat, GovDoc helps the intake desk process documents in a structured and visible way.

### 4.3 Non-technical value statement

- reduce intake delay
- reduce misrouting
- increase status visibility
- support hybrid paper/digital input
- keep a clean trace of AI suggestion vs human decision

---

## 5) MVP boundary

### 5.1 In scope

The MVP must support:

- upload / intake of incoming documents
- support for born-digital files and scan-like files
- automatic metadata extraction
- document-type classification
- concise summary generation
- department-routing suggestion
- confidence + rationale
- human approval / correction
- workflow status tracking
- consultation request / internal note thread
- role-based visibility simulation
- audit trail
- reference retrieval panel
- stable demo mode

### 5.2 Out of scope

The MVP must **not** try to implement:

- real login / password auth
- user self-registration
- tenant management
- a full low-code workflow builder
- arbitrary prompt editing in production UI
- arbitrary tool invocation by AI
- full archival compliance engine
- digital signature workflow
- e-sign integration
- full email ingestion
- production-grade OCR pipeline for every format
- full cross-province interoperability
- real integration with actual government document systems

### 5.3 Design principle

The MVP should look like **a realistic slice of a real system**, not a toy and not a whole platform.

---

## 6) Core workflow to support

### 6.1 Canonical workflow states

The data model and UI should explicitly support these states:

1. `intake_received`
2. `registered`
3. `routed_pending_human_review`
4. `assigned_to_department`
5. `under_review`
6. `consultation_requested`
7. `consultation_completed`
8. `response_prepared`
9. `closed`
10. `archived_demo_only`

### 6.2 State transition expectations

- A document must not jump directly from intake to closed.
- AI suggestions must always be reviewable before final department assignment.
- Consultation must be optional, not mandatory.
- Response preparation can be lightweight in MVP; it is mainly to complete the story.

### 6.3 What must be real vs simulated

For the MVP demo:
- upload, extraction, classification, summary, routing suggestion, and status changes should be real
- some advanced internal collaboration behaviors may be lightly simulated if needed
- demo mode may preload known examples and cached AI results to reduce risk during live presentation

---

## 7) Supported incoming document taxonomy

The hero dataset and the hero use-case will support these administrative document categories:

1. **Công văn**
2. **Quyết định**
3. **Thông báo**
4. **Tờ trình**
5. **Báo cáo**

### 7.1 Why these five categories

These categories are:
- common in official public-sector workflows
- available from public sources
- different enough to show non-trivial classification
- easy for judges to recognize as realistic document types

### 7.2 Optional “other / unknown” category

The system should also support:
- `other`
- `unknown`
- `out_of_scope`

This is important so the demo does not feel overfit or fake-perfect.

---

## 8) Receiving department / routing taxonomy

For MVP, use a **small, believable department list**, not a huge ministry hierarchy.

### 8.1 Recommended department list

- Văn phòng / Records Office
- Legal / Regulatory Affairs
- Finance / Budget
- Internal Affairs / Administration
- Citizen Affairs / Public Service
- Sector Specialist Desk (generic configurable bucket)
- Leadership / Supervisor Review

### 8.2 Why keep it small

A smaller routing set:
- improves demo clarity
- makes labels more defensible
- lowers the burden of AI evaluation
- still proves the routing concept

### 8.3 Routing output shape

Routing output should include:

- `suggested_department`
- `secondary_department` (optional)
- `routing_confidence`
- `routing_rationale`
- `needs_consultation` (boolean)
- `needs_supervisor_review` (boolean)

---

## 9) Confidentiality / security model for MVP

### 9.1 Supported security levels

Use a simple but credible four-level model:

- `unclassified`
- `confidential`
- `secret`
- `top_secret`

### 9.2 Important MVP rule

The system should **display and enforce** simple visibility differences by role, but it should **not** claim to be production-secure.

### 9.3 What security behavior must exist in MVP

- each document has a security level
- each simulated role has an access scope
- restricted views hide content or show masked fields
- every approval / reroute / consultation action is logged
- the original file is retained separately from extracted text

### 9.4 What security behavior may be mocked or simplified

- real IAM / SSO
- real encryption key management UI
- fine-grained field-level production policy engine
- real network segmentation

---

## 10) Role model and login decision

### 10.1 Decision

**Do not implement real login for the MVP.**

### 10.2 Reason

Real login is not core to the hackathon scoring and would consume time that is better spent on:
- workflow
- AI
- UI clarity
- testing
- demo polish

### 10.3 Replace real login with a role switcher

Use a **demo role switcher** that simulates:

- Intake Clerk
- Department Reviewer
- Consultant / Secondary Department
- Supervisor

### 10.4 What role simulation must still prove

Even without real auth, the app must still show:
- different views per role
- restricted access by security level
- different allowed actions
- tracked user/action history

### 10.5 What not to fake

Do not use role simulation to bypass the logic model.
Role-based action restrictions still need to exist in backend/business logic.

---

## 11) Alibaba Cloud stack decisions

This section freezes the selected Alibaba Cloud stack for the MVP.

### 11.1 Core principle

Use a **lean Alibaba-first stack** centered on **Model Studio API**, not the full Alibaba ecosystem.

### 11.2 Selected Alibaba components

#### A. Model Studio API
Primary AI inference layer.

Use for:
- classification
- summarization
- routing suggestion
- response drafting
- evaluation jobs

#### B. Qwen-Plus
Default mainline reasoning model.

Use for:
- document type classification
- structured extraction normalization
- summary generation
- routing suggestion
- consultation summary
- response draft seed

#### C. Qwen-Max
Fallback / escalation model.

Use for:
- ambiguous low-confidence documents
- multi-department routing conflicts
- longer reasoning traces
- harder exception cases

#### D. Qwen-OCR
OCR / visual extraction path for:
- scanned PDFs
- photographed documents
- image-like pages
- poor-quality scan variants

#### E. OSS (Object Storage Service)
Source-of-truth file storage.

Use for:
- original raw uploads
- downloadable evidence files
- preview source files
- future pre-signed / temporary access flow

#### F. STS temporary credentials
Temporary access for OSS.

Use for:
- safer short-lived upload / download access
- explicit “secure by design” narrative in the pitch

#### G. Embedding model (`text-embedding-v4`)
Use for:
- chunk embeddings of normalized text
- reference retrieval
- similarity matching against prior documents / guide corpus

#### H. Text Rerank API
Use for:
- reranking retrieved references before display
- improving top-k relevance in the evidence panel

#### I. Batch Inference API (optional but recommended)
Use for:
- offline quality evaluation
- precomputing AI outputs for demo seeds
- batch scoring of the sample corpus

### 11.3 Components intentionally not made core to MVP

#### Qwen-Doc-Turbo
Do not make this a hard dependency for the MVP main path.

Reason:
- mainline MVP should be stable and simple
- born-digital files can be extracted locally / deterministically
- scan path is already covered by Qwen-OCR

#### Qwen-Long
Do not make this a hard dependency for the MVP.
The selected use-case does not require a dedicated long-context-first architecture.

#### Full deployment on Alibaba Cloud
Not required for MVP success.
It is acceptable to deploy elsewhere while still using Qwen via API.

---

## 12) Integration strategy per Alibaba component

### 12.1 OSS integration

#### Purpose
Store the original uploaded file as the source of truth.

#### Required behavior
- every uploaded document gets an `oss_object_key`
- original file is never discarded
- preview/download should refer back to stored original
- extraction outputs are stored separately from the original

#### Notes
For the baseline app, local storage may be used first behind an abstraction, but the architecture and contracts must already assume OSS.

### 12.2 STS integration

#### Purpose
Use temporary credentials when/if browser-direct upload is introduced.

#### MVP rule
The baseline may initially upload through backend only, but the design must be compatible with later STS/browser upload.

#### What to preserve in architecture
- upload adapter abstraction
- no UI dependence on permanent credentials
- future-proof contract for signed upload / temporary token flow

### 12.3 Qwen-OCR integration

#### Trigger conditions
Use Qwen-OCR when:
- file is image-only PDF
- deterministic extraction returns too little text
- user marks document as scan/photo
- demo scenario explicitly requires scan path

#### Output contract
Return at minimum:
- extracted text
- page count
- OCR quality estimate or heuristic score
- extraction warnings

#### MVP note
Do not overbuild layout reconstruction.
Plain text + page references is enough.

### 12.4 Qwen-Plus integration

#### Mainline prompt responsibilities
Qwen-Plus should accept normalized text + metadata + allowed labels and return structured JSON for:

- document type
- short summary
- issuing agency guess (optional if not extracted deterministically)
- topic / subject
- urgency guess
- confidentiality guess
- suggested department
- secondary department
- confidence
- rationale
- “needs human review” flags

#### Output format requirement
Use **strict JSON schema / structured output** as much as possible.
Do not rely on freeform prose for core decisions.

### 12.5 Qwen-Max integration

#### Trigger conditions
Escalate to Qwen-Max when:
- mainline confidence < threshold
- multiple department candidates are too close
- document is very long or mixed-purpose
- deterministic rules detect ambiguity
- QA scenario explicitly tests difficult reasoning

#### Output requirement
Qwen-Max should return:
- final recommendation
- alternative department(s)
- explanation of ambiguity
- recommendation on whether consultation is needed

### 12.6 Embeddings integration

#### What to embed
Embed only normalized text chunks from:
- selected reference corpus
- workflow guides
- optionally previously processed documents

#### What not to embed in MVP
Do not embed:
- raw binary file content
- every tiny OCR fragment
- unrestricted sensitive material without filtering

### 12.7 Rerank integration

#### Purpose
Improve the quality of the evidence panel shown to users.

#### Recommended retrieval flow
1. chunk reference text
2. embed chunks
3. retrieve top-k approximate candidates
4. rerank candidates
5. show top evidence items with snippets

### 12.8 Batch inference integration

#### Use cases
- generate evaluation artifacts offline
- precompute stable AI outputs for seeded demo documents
- compare prompt versions on the sample corpus

#### MVP note
Batch is optional for the first runnable baseline, but highly recommended before final demo/pitch polish.

---

## 13) File handling decision: raw file vs extracted text

### 13.1 Decision

**Keep both the raw original file and a normalized extracted representation.**

This is a hard decision and should not change later without a good reason.

### 13.2 Why not “raw only”
Using raw files for every reasoning step is:
- more expensive
- harder to cache
- harder to inspect
- harder to evaluate
- less explainable

### 13.3 Why not “text only”
Using text only loses:
- source-of-truth evidence
- auditability
- preview fidelity
- scan fallback traceability

### 13.4 Final handling strategy

#### Born-digital PDF / DOCX
- store raw in OSS / file store
- extract text deterministically in backend
- build normalized JSON
- feed normalized content to Qwen-Plus

#### Scanned PDF / image-heavy PDF / photo
- store raw in OSS / file store
- run Qwen-OCR
- normalize OCR output to text + metadata
- feed normalized content to Qwen-Plus
- escalate to Qwen-Max only if needed

#### Image files
- same as scan path

### 13.5 Normalized artifact schema

Each processed document should have a normalized artifact containing at least:

- document id
- original filename
- mime type
- page count
- extracted text
- extracted text by page (optional but recommended)
- extraction method
- extraction warnings
- deterministic metadata
- AI classification output
- AI routing output
- audit timestamps

---

## 14) Deterministic logic vs AI logic

### 14.1 Deterministic logic should handle

- file validation
- mime / extension checks
- page count
- storage keys
- workflow state transitions
- role-based action permissions
- confidence threshold gates
- audit logs
- routing guardrails
- summary length constraints
- prompt version references

### 14.2 AI logic should handle

- semantic type classification
- subject/topic understanding
- summary generation
- department suggestion
- ambiguity reasoning
- consultation recommendation
- evidence summarization

### 14.3 Important principle

Do not let the model directly mutate system state.
The model should recommend; the application should decide and persist.

---

## 15) Safe configurability for MVP

The MVP should feel adaptable, but must not become a full platform builder.

### 15.1 Safe things to make configurable

1. document taxonomy labels
2. department list
3. routing rules table
4. extraction field schema
5. security labels
6. prompt templates
7. prompt version selection
8. confidence thresholds
9. summary format template
10. retrieval corpus selection
11. UI text / naming per organization

### 15.2 Things that should not be widely configurable in MVP

1. auth model
2. unrestricted permission policies
3. arbitrary workflow builder
4. freeform agent-tool execution
5. unrestricted model parameter editing by end users
6. live editing of core system prompts without version control
7. uncontrolled escalation rules

### 15.3 Reason for bounded configurability

We want to show:
- “this is not overfit to one example”
without
- making the system unstable
- making testing impossible
- opening large prompt/logic drift during the hackathon

---

## 16) Baseline app expectations for Google AI Studio generation

The baseline app generated with Google AI Studio should be **real frontend + real backend + mock business logic**.

### 16.1 What the baseline must include

- real screens and navigation
- real entity structure
- real backend API surface
- realistic seed records
- mock business logic
- simulation toggles where useful for demo
- room to replace mocks with real logic later

### 16.2 What the baseline should not do

- invent wrong entity models
- collapse everything into one chat UI
- hardcode a single static sample everywhere
- hide the workflow behind generic agent chat

### 16.3 Required baseline entity model

At minimum the baseline should already contain entities like:

- document
- document_file
- extracted_artifact
- ai_analysis
- routing_decision
- consultation_note
- audit_event
- role
- department
- demo_scenario
- prompt_version

### 16.4 Mocking rule

The baseline may mock:
- classification result
- routing result
- confidence values
- retrieval results
- consultation thread auto-responses

But the baseline should preserve the exact **contracts** that later real logic will satisfy.

---

## 17) Web UI scene map expectations

### 17.1 Scene 0 — Demo home / role switcher
Purpose:
- choose simulated role
- choose demo scenario
- show system overview / queue counts

### 17.2 Scene 1 — Intake queue
Purpose:
- upload document
- preview source file
- show incoming queue
- start analysis

Key fields:
- source channel
- filename
- received time
- preliminary security level
- ingest status

### 17.3 Scene 2 — Record detail / AI analysis
Purpose:
- inspect one document deeply

Must show:
- original document preview
- extracted text preview
- extracted metadata
- document type prediction
- short summary
- urgency/confidentiality guess
- proposed department
- confidence
- rationale
- evidence / similar references panel

### 17.4 Scene 3 — Review / routing approval
Purpose:
- human validates or corrects AI output

Actions:
- approve
- change category
- reroute
- request consultation
- escalate to supervisor
- mark as out-of-scope

### 17.5 Scene 4 — Consultation thread
Purpose:
- request and view cross-department input

Must show:
- requester
- requested department
- reason
- notes thread
- timestamps
- current resolution state

### 17.6 Scene 5 — Tracking dashboard
Purpose:
- show lifecycle visibility

Must show:
- state timeline
- owner department
- due / pending flags
- audit trail summary
- queue distribution

### 17.7 Scene 6 — Response / closeout
Purpose:
- complete the story from intake to response

Must show:
- disposition note or response draft
- final department / owner
- closure timestamp
- archive-ready state

---

## 18) Demo strategy and seeded scenarios

### 18.1 Hero demo path
The main demo should be:

1. intake clerk uploads incoming document
2. system extracts text
3. system classifies document type
4. system generates summary
5. system suggests target department
6. human reviews and approves
7. department reviewer opens case
8. consultation is requested
9. consultation response arrives
10. supervisor sees tracked progression
11. response/disposition is prepared
12. case is closed

### 18.2 Secondary demo path: ambiguity
Use one document where:
- two departments are plausible
- confidence is lower
- the system recommends consultation or supervisor review

### 18.3 Secondary demo path: scan robustness
Use a derived low-quality scan sample so the demo can show:
- OCR path
- extraction fallback
- still-usable classification/summarization

### 18.4 Demo mode requirement
The app should support:
- seeded demo records
- cached AI outputs if needed
- replayable scenarios
- stable UI states even if live inference is slow

---

## 19) Data-pack decisions

### 19.1 Current bundled full pack

The bundled full pack now includes:

#### Incoming administrative docs
- 13 công văn
- 13 quyết định
- 8 thông báo
- 8 tờ trình
- 8 báo cáo

#### Hard cases
- 8 scanned-low-quality variants
- 6 multi-department cases
- 6 out-of-scope cases

#### Reference corpus
- 20 gov-docs HTML/PDF corpus items
- 15 legal-reference items
- 10 court-judgment items

#### Labels
- `manifest.csv`
- `routing_ground_truth.csv`
- `summary_expectations.jsonl`
- `security_levels.csv`

### 19.2 Important note on reference-corpus quality

The full pack is materially better than the earlier starter subset, but it is still a **hackathon-ready bootstrap corpus**, not a final gold-standard research dataset.

Specifically:
- `incoming/`, `hard-cases/`, and `reference-corpus/gov-docs-html-or-pdf/` are mostly bundled PDFs
- `reference-corpus/legal-reference/` is bundled as lightweight reference stubs with official source URLs and relevance notes
- `reference-corpus/court-judgments/` is bundled as source stubs because direct automated court-portal PDF downloading was unreliable from this environment

### 19.3 What this full pack is now good enough for

This full pack is now good enough for:
- baseline UI seeding
- implementation handoff prep
- routing/taxonomy design
- OCR robustness testing
- retrieval/index design
- AI quality evaluation scaffolding
- hero demo + ambiguity demo + scan demo
- first-pass E2E scenario preparation

### 19.4 Labeling work still required later

Later plans should create ground-truth labels for:

- document type
- issuing body
- target department
- optional secondary department
- urgency
- confidentiality
- gold summary bullets
- ambiguous-case notes
- known hard / low-quality flags

---

## 20) Sample corpus usage by category

### 20.1 Công văn
Use for:
- general intake
- subject extraction
- recipient-based routing
- common official correspondence

### 20.2 Quyết định
Use for:
- more formal administrative action documents
- longer structural extraction
- decision / action-oriented department mapping

### 20.3 Thông báo
Use for:
- notice-type categorization
- lower-ambiguity fast classification
- date / schedule-heavy extraction

### 20.4 Tờ trình
Use for:
- proposal / submission style docs
- recommendation to leadership
- routing to leadership/legal/internal affairs patterns

### 20.5 Báo cáo
Use for:
- longer texts
- summarization quality
- report vs directive differentiation

### 20.6 Workflow guide references
Use for:
- retrieval grounding
- evidence panel
- workflow explanation
- UI content for “why routed here” or “what is the handling process”

### 20.7 Derived scan variants
Use for:
- Qwen-OCR path
- low-quality robustness
- scan-vs-born-digital pipeline testing

---

## 21) Routing philosophy for MVP

### 21.1 AI recommends; humans decide
The system suggests routing.
The human reviewer approves or corrects.

### 21.2 Confidence thresholds
Recommended conceptually:

- high confidence: auto-fill recommendation, still human-reviewable
- medium confidence: flag for explicit human confirmation
- low confidence: suggest consultation / supervisor review

### 21.3 Multi-department cases
Do not force a fake single-answer output.
Allow:
- primary department
- secondary department
- consultation suggestion

---

## 22) Retrieval / evidence panel expectations

### 22.1 Purpose
The evidence panel makes the system feel:
- grounded
- non-black-box
- more credible to judges

### 22.2 What it should show
For each analyzed document:
- similar reference items
- workflow guide snippets
- why those references were selected
- optional “related previously processed documents” in demo mode

### 22.3 What it should not try to be
- full legal research engine
- full RAG chatbot
- open-ended question answering product

---

## 23) Expected quality posture

### 23.1 Honest quality target
The MVP does not need to claim perfect classification or perfect routing.

### 23.2 Desired impression
The system should look:
- realistic
- helpful
- controllable
- audit-friendly
- explainable

### 23.3 Better to show
- one lower-confidence case with a correct escalation path
than
- fake-perfect outputs everywhere

---

## 24) Architecture expectations

### 24.1 Logical components

1. frontend web app
2. backend API
3. file storage adapter
4. extraction pipeline
5. AI analysis service
6. retrieval/indexing service
7. workflow state service
8. audit log service
9. demo scenario seeder

### 24.2 Separation requirement
The codebase should clearly separate:
- UI state
- business workflow state
- AI adapter layer
- deterministic rules
- data storage layer

This is important so later coding-agent plans can implement core logic safely without rewriting the UI.

---

## 25) Prompting and structured-output expectations

### 25.1 Prompt families to maintain

At minimum, maintain separate prompt families for:

- classification
- summarization
- routing
- ambiguity escalation
- consultation summary
- response draft seed

### 25.2 Prompt versioning rule
Every result shown in the system should be traceable to:
- model name
- prompt family
- prompt version
- timestamp

### 25.3 JSON-first rule
Core outputs must be structured.
Freeform prose may be displayed as explanatory text, but not used as the only machine-readable source.

---

## 26) Baseline acceptance expectations

The baseline generated via Google AI Studio is acceptable if:

- it already uses the correct document/workflow entities
- it already has the right screens
- it already supports seeded scenarios
- the core AI/business logic is replaceable without redesigning the app

The baseline is **not** acceptable if:

- it is basically a generic chat app
- it has no document detail page
- it has no explicit workflow states
- it has no review/approval scene
- it collapses records, routing, and consultation into one screen without structure

---

## 27) Risks and mitigations

### Risk 1: Over-scope
Mitigation:
- keep one target use-case
- keep one department taxonomy
- keep one clear end-to-end story

### Risk 2: Live model latency or quota issues
Mitigation:
- cached seeded AI outputs
- demo mode
- use Qwen-Plus mainline and Qwen-Max only on escalation

### Risk 3: OCR path instability
Mitigation:
- limit scan demo to a few curated cases
- keep deterministic born-digital extraction as mainline

### Risk 4: Dataset too narrow
Mitigation:
- use documents from multiple provinces/agencies
- include an “unknown / other” class
- include reference guides and derived hard cases

### Risk 5: UI feels fake because no login
Mitigation:
- explicit role switcher
- real role-based differences in actions and visibility
- backend permission checks still enforced

---

## 28) Decisions frozen by this document

The following decisions are intentionally frozen:

1. **Selected use-case** = incoming administrative document intake + triage
2. **Hero taxonomy** = công văn / quyết định / thông báo / tờ trình / báo cáo
3. **No real login** for MVP
4. **Use role simulation**
5. **Use Alibaba Model Studio as core AI stack**
6. **Use Qwen-Plus as default**
7. **Use Qwen-Max only for escalation**
8. **Use Qwen-OCR for scans**
9. **Keep raw file + normalized artifact**
10. **Support reference retrieval panel**
11. **Optimize for one polished flow, not a broad platform**
12. **Baseline app may mock logic but must use final entity/scene structure**

---

## 29) Items intentionally deferred to later plans

These should be decided in later documents, not here:

- concrete repo/file structure
- API endpoint definitions
- DB schema details
- implementation pass breakdown
- unit test inventory
- AI quality score thresholds
- Playwright scenario scripts
- Makefile/CI steps
- Docker compose details
- exact seeded prompts and cached result strategy

---

## 30) Immediate next deliverables after this source-of-truth note

The next handoffs should be generated in this order:

1. **submission rewrite**
2. **implementation plan**
3. **test plan**
4. **demo plan**
5. **seeded scenario sheet**
6. **AI evaluation plan**
7. **coding-agent handoff notes**

---

## 31) Appendix A — included data-pack summary

Bundled sample pack path:
- `govdoc_data_pack_full.zip`

Included top-level folders:
- `incoming/`
- `hard-cases/`
- `reference-corpus/`
- `labels/`
- `README.md`

See `labels/manifest.csv` for:
- relative path
- file type / size
- SHA-256 hash

See the other files in `labels/` for bootstrap routing, summary, and security annotations.

---

## 32) Appendix B — guiding implementation posture

When implementing the real logic later:

- prefer deterministic guards around AI
- keep AI outputs inspectable
- keep UI states demo-friendly
- keep business state explicit
- never hide ambiguity if the system is unsure
- never over-claim security or automation that the MVP does not truly implement

---

## 33) Final statement

The winning version of GovDoc SecureFlow for this hackathon is **not** “AI for all government documents”.

It is:

> a secure, end-to-end AI-assisted intake, classification, summarization, routing, and tracking workflow for incoming administrative documents, with human approval, role-based visibility, and clear Alibaba/Qwen integration.

Everything after this document should preserve that direction.
