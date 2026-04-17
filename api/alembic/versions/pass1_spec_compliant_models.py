"""Pass 1 — spec-compliant models with UUID PKs and correct enums

Revision ID: pass1_spec_models
Revises: None (fresh start)
Create Date: 2026-04-17

"""

from alembic import op
import sqlalchemy as sa


revision = "pass1_spec_models"
down_revision = None
branch_labels = None
depends_on = None


# All table names in dependency order
_ALL_TABLES = [
    "roles",
    "departments",
    "documents",
    "document_files",
    "extracted_artifacts",
    "ai_analysis",
    "routing_decisions",
    "consultation_notes",
    "audit_events",
    "prompt_versions",
    "demo_scenarios",
]


def upgrade():
    # ---- Drop old tables if they exist (fresh dev DB) ----
    for table in _ALL_TABLES:
        op.drop_table(table, if_exists=True)

    # ---- Create tables in dependency order ----

    op.create_table(
        "roles",
        sa.Column("id", sa.String(50), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("allowed_actions", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "departments",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("doc_number", sa.String(100), nullable=True),
        sa.Column("issuing_agency", sa.String(255), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status", sa.String(20), nullable=False, server_default="received"),
        sa.Column("security_level", sa.String(20), nullable=False, server_default="unclassified"),
        sa.Column("urgency", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("assigned_department_id", sa.String(36), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("assigned_reviewer_role", sa.String(50), nullable=True),
        sa.Column("current_prompt_version", sa.String(12), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "document_files",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("1"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "extracted_artifacts",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("extraction_method", sa.String(20), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_count", sa.Integer(), server_default=sa.text("1"), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ai_analysis",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(12), nullable=False),
        sa.Column("source", sa.String(10), server_default="live", nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "routing_decisions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("suggested_department_id", sa.String(36), nullable=True),
        sa.Column("final_department_id", sa.String(36), nullable=True),
        sa.Column("decided_by_role", sa.String(50), nullable=True),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "consultation_notes",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("author_role", sa.String(50), nullable=False),
        sa.Column("target_role", sa.String(50), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("actor_role", sa.String(50), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("from_state", sa.String(50), nullable=True),
        sa.Column("to_state", sa.String(50), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", "stage"),
    )

    op.create_table(
        "demo_scenarios",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    # Drop all tables in reverse dependency order
    for table in reversed(_ALL_TABLES):
        op.drop_table(table, if_exists=True)
