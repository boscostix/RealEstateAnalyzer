"""Create properties and analyses tables."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260807_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "properties",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("listing_id", sa.String(length=255), nullable=True),
        sa.Column("full_address", sa.String(length=512), nullable=True),
        sa.Column("street", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=True),
        sa.Column("postal_code", sa.String(length=32), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("normalized_property_json", sa.JSON(), nullable=True),
        sa.Column("verified_property_json", sa.JSON(), nullable=True),
        sa.Column("property_schema_version", sa.String(length=32), nullable=False),
        sa.Column("verified_property_schema_version", sa.String(length=32), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_properties_city", "properties", ["city"], unique=False)
    op.create_index("ix_properties_created_at", "properties", ["created_at"], unique=False)
    op.create_index("ix_properties_full_address", "properties", ["full_address"], unique=False)
    op.create_index("ix_properties_listing_id", "properties", ["listing_id"], unique=False)
    op.create_index("ix_properties_postal_code", "properties", ["postal_code"], unique=False)
    op.create_index("ix_properties_provider", "properties", ["provider"], unique=False)
    op.create_index("ix_properties_state", "properties", ["state"], unique=False)
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("property_id", sa.String(length=36), nullable=False),
        sa.Column("parent_analysis_id", sa.String(length=36), nullable=True),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="analysisstatus"),
            nullable=False,
        ),
        sa.Column(
            "current_stage",
            sa.Enum(
                "preparation",
                "underwriting",
                "research",
                "agent_research",
                "investment_committee",
                "persistence",
                name="analysisstage",
            ),
            nullable=True,
        ),
        sa.Column(
            "failure_stage",
            sa.Enum(
                "preparation",
                "underwriting",
                "research",
                "agent_research",
                "investment_committee",
                "persistence",
                name="analysisstage",
            ),
            nullable=True,
        ),
        sa.Column("property_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("assumptions_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("underwriting_result_json", sa.JSON(), nullable=True),
        sa.Column("research_result_json", sa.JSON(), nullable=True),
        sa.Column("agent_research_result_json", sa.JSON(), nullable=True),
        sa.Column("investment_committee_result_json", sa.JSON(), nullable=True),
        sa.Column("execution_metadata_json", sa.JSON(), nullable=True),
        sa.Column("analysis_schema_version", sa.String(length=32), nullable=False),
        sa.Column("report_schema_version", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parent_analysis_id"], ["analyses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_id", "version", name="uq_analyses_property_version"),
    )
    op.create_index("ix_analyses_created_at", "analyses", ["created_at"], unique=False)
    op.create_index(
        "ix_analyses_parent_analysis_id",
        "analyses",
        ["parent_analysis_id"],
        unique=False,
    )
    op.create_index(
        "ix_analyses_property_created",
        "analyses",
        ["property_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_analyses_property_id", "analyses", ["property_id"], unique=False)
    op.create_index("ix_analyses_status", "analyses", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_analyses_status", table_name="analyses")
    op.drop_index("ix_analyses_property_id", table_name="analyses")
    op.drop_index("ix_analyses_property_created", table_name="analyses")
    op.drop_index("ix_analyses_parent_analysis_id", table_name="analyses")
    op.drop_index("ix_analyses_created_at", table_name="analyses")
    op.drop_table("analyses")
    op.drop_index("ix_properties_state", table_name="properties")
    op.drop_index("ix_properties_provider", table_name="properties")
    op.drop_index("ix_properties_postal_code", table_name="properties")
    op.drop_index("ix_properties_listing_id", table_name="properties")
    op.drop_index("ix_properties_full_address", table_name="properties")
    op.drop_index("ix_properties_created_at", table_name="properties")
    op.drop_index("ix_properties_city", table_name="properties")
    op.drop_table("properties")
