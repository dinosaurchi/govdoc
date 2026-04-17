# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added

- AI document analysis pipeline with Qwen models via Model Studio integration
- Document intake with multipart file upload and artifact persistence
- AI-powered document classification and routing
- Multi-role workflow supporting Intake Clerk, Reviewer, Consultant, and Supervisor roles
- Document status state machine with 11 statuses and backend transition validation
- Consultation workflow with reroute and resolve-consultation endpoints
- RAG-based document retrieval
- Audit trail for all document actions
- Dashboard with analytics and document tracking
- Role-based access control across the application
- State-aware workflow action panel with centralized action model
- Reroute form UI with success button variant
- Frontend migrated to Vite 6 + React Router v7 (from Next.js 15)
- React 19 frontend with TypeScript, Tailwind CSS v4, and Lucide icons
- FastAPI backend with SQLAlchemy, Alembic migrations, and Pydantic schemas
- Docker containerization with docker-compose for full-stack deployment
- GitHub Actions CI/CD pipeline with linting, testing, and build stages
- Comprehensive test suite: Vitest (unit), Pytest (API), and Playwright (E2E)
- Development workflow scripts and Makefile for common tasks
- Project documentation including contributing guide and agent rules

### Fixed

- Corrected `canReroute` transition logic to match backend state machine (`in_consultation` → `routed` is invalid)
- Fixed CI workflow to install web dependencies and correct npm cache path
- Updated `.gitignore` to exclude `api/data` directory
