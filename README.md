# GovDoc SecureFlow

**AI-powered government document processing with intelligent routing, classification, and multi-role workflow.**

![Python](https://img.shields.io/badge/python-3.12-blue)
![React](https://img.shields.io/badge/react-19-61dafb)
![FastAPI](https://img.shields.io/badge/fastAPI-0.115-009688)
![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)
![CI](https://img.shields.io/badge/CI-passing-brightgreen)
![Tests](https://img.shields.io/badge/tests-224%20passing-brightgreen)

---

## What is GovDoc SecureFlow?

GovDoc SecureFlow is an end-to-end platform that transforms how government agencies handle incoming documents. Built for the **Qwen AI Build Day 2026** hackathon, it leverages Alibaba's Qwen family of large language models to automatically analyze, classify, and route Vietnamese government documents — from intake to final disposition.

Government offices process thousands of official documents daily — công văn (dispatches), quyết định (decisions), thông báo (notices), tờ trình (proposals), and báo cáo (reports). Each requires careful handling by the right department, with proper consultation and approval chains. GovDoc SecureFlow automates the tedious parts while preserving human oversight through a structured, role-based workflow.

The result: faster processing, fewer routing errors, built-in audit trails, and an AI assistant that surfaces relevant precedents and suggests next steps — all through a clean, modern web interface.

---

## Features

### 🤖 AI-Powered Analysis
- **Document classification** — Qwen models identify document type, priority, and subject matter
- **Content extraction** — Structured data pulled from text, PDFs, and scanned images (via `qwen-vl-plus` vision)
- **Smart summarization** — Key points and action items generated automatically
- **Semantic embeddings** — `text-embedding-v4` with `qwen3-rerank` for precise retrieval

### 🔄 Intelligent Workflow
- **11-state document lifecycle** with strict state machine transitions
- **5 document types**: Công văn, Quyết định, Thông báo, Tờ trình, Báo cáo
- **Automated routing** to the correct department based on AI analysis
- **Consultation workflow** — request input from other departments with AI-drafted consultation notes

### 👥 Simulated Multi-Role Workflow
- **4 role perspectives** for demo: Intake Clerk, Department Reviewer, Consultant, Supervisor
- Each role showcases a tailored view of the document workflow
- Demonstrates how different stakeholders interact with the system
- Full audit trail shows actions attributed to each role

### 🔍 Retrieval-Augmented Generation
- Search across the full document corpus using natural language
- RAG pipeline surfaces relevant precedents and related documents
- Evidence panel shows source citations for every AI suggestion

### 📋 Audit & Compliance
- Complete action history for every document
- Dashboard analytics showing processing metrics and bottlenecks
- Filterable, searchable document archive

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────┐
│   Web UI    │────▶│  FastAPI API  │────▶│  Alibaba Model      │
│  React 19   │     │  Python 3.12  │     │  Studio (Qwen)      │
└─────────────┘     └──────┬───────┘     └─────────────────────┘
                           │
                    ┌──────▼───────┐
                    │   SQLite     │
                    │   (WAL)      │
                    └──────────────┘
```

The frontend proxies all API calls through Vite's dev server (or Nginx in production). The backend exposes a RESTful API and communicates with Alibaba Model Studio for AI capabilities. SQLite with WAL mode provides lightweight, reliable persistence.

---

## Document Workflow

Every document follows a strict state machine that ensures proper handling:

```
received → extracted → analyzed → routed → under_review → in_consultation → approved → closed
                                            │              │               │
                                            └──► out_of_scope ◄──────────┘
```

| State | Description |
|-------|-------------|
| `received` | Document uploaded, awaiting processing |
| `extracted` | Text/content extracted from file |
| `analyzed` | AI classification and summarization complete |
| `routed` | Assigned to a department |
| `under_review` | Department reviewer is evaluating |
| `in_consultation` | External input requested from another department |
| `approved` | Document reviewed and approved |
| `closed` | Processing complete |
| `out_of_scope` | Document does not require action |

---

## Quick Start

### Prerequisites

- **Docker** & **Docker Compose** v2
- **Node.js** 20+ (for local development)
- **Python** 3.12+ (for local development)

### Setup

```bash
# 1. Clone the repository
git clone <repo-url> && cd govdoc

# 2. Configure environment
cp .env.example .env
# Edit .env with your Model Studio API key and preferences

# 3. Start all services
make up

# 4. Seed demo data (optional)
make seed-demo

# 5. Open your browser
#    http://localhost:3000
```

---

## Development

| Command | Description |
|---------|-------------|
| `make up` | Start all services (Docker) |
| `make down` | Stop all services |
| `make ci` | Run full CI pipeline (lint → build → test) |
| `make test` | Run all tests (frontend + backend) |
| `make lint` | Lint frontend (ESLint) and backend (Ruff) |
| `make seed-demo` | Seed demo documents and reference corpus |
| `make logs` | Follow service logs |
| — | API health: `http://localhost:8000/readyz` |

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for detailed development guidelines.

---

## Project Structure

```
govdoc/
├── web/                  # Frontend — React 19 + Vite 6 + TypeScript + Tailwind v4
│   ├── src/              # React components, pages, hooks, and services
│   ├── tests-e2e/        # Playwright E2E test specs
│   └── public/           # Static assets
├── api/                  # Backend — FastAPI + SQLAlchemy 2.x + Alembic
│   ├── app/              # Application code (routes, services, models, adapters)
│   ├── tests/            # Pytest suites (unit, integration, contract)
│   ├── alembic/          # Database migration scripts
│   ├── config/           # Model configuration (models.yaml)
│   └── prompts/          # AI prompt templates
├── deploy/               # Dockerfiles (Dockerfile.api, Dockerfile.web)
├── scripts/              # Utility scripts (seeding, QA, credentials)
├── e2e/                  # Playwright E2E test project
├── docs/                 # Documentation, demo scripts, implementation plans
└── data/                 # Runtime data (SQLite DB, uploads) — gitignored
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 19 + Vite 6 + TypeScript | Component-based UI with fast HMR |
| Styling | Tailwind CSS v4 | Utility-first CSS framework |
| Backend | FastAPI (Python 3.12) | Async REST API with OpenAPI docs |
| ORM | SQLAlchemy 2.x + Alembic | Database models and migrations |
| Database | SQLite (WAL mode) | Lightweight, zero-config persistence |
| AI Models | Qwen (via Model Studio) | Analysis, classification, embeddings, vision, rerank |
| Containerization | Docker + Docker Compose | Reproducible dev and deployment |
| E2E Testing | Playwright | Browser automation tests |

### AI Models

| Model | Purpose |
|-------|---------|
| `qwen-plus` | Primary analysis and classification |
| `qwen-max` | Complex reasoning and summarization |
| `qwen-vl-plus` | Vision — OCR and scanned document processing |
| `text-embedding-v4` | Semantic search embeddings |
| `qwen3-rerank` | Search result re-ranking for RAG pipeline |

---

## Demo Roles

> **Note:** Role switching is a demo simulation to showcase the multi-stakeholder workflow. This is not a production authentication system.

| Role | Demonstrates |
|------|-------------|
| **Intake Clerk** | Document upload, AI extraction, initial processing |
| **Department Reviewer** | Document review, consultation requests, routing decisions |
| **Consultant** | Responding to consultation requests |
| **Supervisor** | Full oversight, analytics, final approval and closeout |

---

## Testing

| Layer | Tool | Coverage |
|-------|------|----------|
| Frontend (unit) | Vitest | 45 tests — components, hooks, services |
| Backend (unit + integration + contract) | Pytest | 224 tests — services, routes, state machine, adapters |
| E2E | Playwright | Browser-based acceptance tests |
| CI | GitHub Actions | Runs `make ci` on every push and PR |

Run all tests:

```bash
make test          # Frontend + backend
make test-e2e      # End-to-end (requires running stack)
```

---

## Acknowledgments

Built for **Qwen AI Build Day 2026** — a hackathon showcasing what's possible with Alibaba Cloud's Model Studio and the Qwen model family.

Powered by [Alibaba Cloud Model Studio](https://www.alibabacloud.com/en/products/model-studio) and the [Qwen](https://qwen.readthedocs.io/) family of large language models.

---
