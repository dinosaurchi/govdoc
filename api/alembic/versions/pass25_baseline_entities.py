"""Pass 2.5 — document_file, extracted_artifact, ai_analysis, audit_events, column fixes

Revision ID: pass25_baseline
Revises: 1a2b3c4d5e6f
Create Date: 2026-04-17

"""
from alembic import op
import sqlalchemy as sa


revision = "pass25_baseline"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    insp = sa.inspect(bind)
    return name in insp.get_table_names()


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade():
    bind = op.get_bind()

    if not _has_table(bind, "document_files"):
        op.create_table(
            "document_files",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("document_id", sa.Integer(), nullable=False),
            sa.Column("file_name", sa.String(), nullable=False),
            sa.Column("mime_type", sa.String(), nullable=False),
            sa.Column("file_size_bytes", sa.Integer(), nullable=False),
            sa.Column("storage_relative_path", sa.String(), nullable=False),
            sa.Column("sha256_hex", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_document_files_id"), "document_files", ["id"], unique=False)

    if not _has_table(bind, "extracted_artifacts"):
        op.create_table(
            "extracted_artifacts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("document_id", sa.Integer(), nullable=False),
            sa.Column("document_file_id", sa.Integer(), nullable=True),
            sa.Column("extraction_method", sa.String(), nullable=False),
            sa.Column("extraction_source_label", sa.String(), nullable=False),
            sa.Column("extracted_text", sa.Text(), nullable=False),
            sa.Column("structured_metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
            sa.ForeignKeyConstraint(["document_file_id"], ["document_files.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_extracted_artifacts_id"), "extracted_artifacts", ["id"], unique=False)

    if not _has_table(bind, "ai_analysis"):
        op.create_table(
            "ai_analysis",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("document_id", sa.Integer(), nullable=False),
            sa.Column("suggested_type", sa.String(), nullable=True),
            sa.Column("urgency_score", sa.Integer(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("suggested_department", sa.String(), nullable=True),
            sa.Column("raw_response", sa.Text(), nullable=True),
            sa.Column("analysis_source_label", sa.String(), nullable=False, server_default="mock_ai_provider"),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ai_analysis_id"), "ai_analysis", ["id"], unique=False)

    if not _has_table(bind, "audit_events"):
        op.create_table(
            "audit_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("document_id", sa.Integer(), nullable=True),
            sa.Column("actor_role_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
            sa.ForeignKeyConstraint(["actor_role_id"], ["roles.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_audit_events_id"), "audit_events", ["id"], unique=False)

    if _has_table(bind, "routing_decisions") and not _has_column(bind, "routing_decisions", "note"):
        op.add_column("routing_decisions", sa.Column("note", sa.Text(), nullable=True))
    if _has_table(bind, "routing_decisions") and not _has_column(bind, "routing_decisions", "created_at"):
        op.add_column("routing_decisions", sa.Column("created_at", sa.DateTime(), nullable=True))

    if _has_table(bind, "consultation_notes") and not _has_column(bind, "consultation_notes", "created_at"):
        op.add_column("consultation_notes", sa.Column("created_at", sa.DateTime(), nullable=True))


def downgrade():
    pass
