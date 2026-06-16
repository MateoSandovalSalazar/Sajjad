"""Initial schema — users, domains, scans, findings, subscriptions.

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "email", sa.String(255), nullable=False, unique=True
        ),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "full_name", sa.String(255), nullable=False, default=""
        ),
        sa.Column(
            "company", sa.String(255), nullable=False, default=""
        ),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, default=True
        ),
        sa.Column(
            "is_verified", sa.Boolean, nullable=False, default=False
        ),
        sa.Column(
            "email_verification_token",
            sa.String(512),
            nullable=True,
        ),
        sa.Column(
            "password_reset_token", sa.String(512), nullable=True
        ),
        sa.Column(
            "password_reset_expires",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── subscriptions ─────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "plan", sa.String(32), nullable=False, default="free"
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "cancelled",
                "expired",
                "pending",
                name="subscriptionstatus",
            ),
            nullable=False,
            default="active",
        ),
        sa.Column(
            "mp_subscription_id",
            sa.String(128),
            nullable=True,
            unique=True,
        ),
        sa.Column("mp_payer_id", sa.String(128), nullable=True),
        sa.Column(
            "mp_preapproval_plan_id",
            sa.String(128),
            nullable=True,
        ),
        sa.Column(
            "current_period_start",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "current_period_end",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "cancelled_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "scans_this_month",
            sa.Integer,
            nullable=False,
            default=0,
        ),
        sa.Column(
            "scans_reset_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_subscriptions_user_id",
        "subscriptions",
        ["user_id"],
    )

    # ── domains ───────────────────────────────────────────
    op.create_table(
        "domains",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fqdn", sa.String(255), nullable=False),
        sa.Column(
            "verification_token", sa.String(64), nullable=False
        ),
        sa.Column(
            "verified_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id", "fqdn", name="uq_user_domain"
        ),
    )
    op.create_index("ix_domains_user_id", "domains", ["user_id"])
    op.create_index("ix_domains_fqdn", "domains", ["fqdn"])

    # ── scans ─────────────────────────────────────────────
    op.create_table(
        "scans",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "domain_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("domains.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "completed",
                "failed",
                name="scanstatus",
            ),
            nullable=False,
            default="pending",
        ),
        sa.Column(
            "progress_stage", sa.String(64), nullable=True
        ),
        sa.Column("risk_score", sa.Integer, nullable=True),
        sa.Column("risk_level", sa.String(16), nullable=True),
        sa.Column(
            "subdomains_count",
            sa.Integer,
            nullable=False,
            default=0,
        ),
        sa.Column(
            "live_hosts_count",
            sa.Integer,
            nullable=False,
            default=0,
        ),
        sa.Column(
            "open_ports_count",
            sa.Integer,
            nullable=False,
            default=0,
        ),
        sa.Column(
            "findings_count",
            sa.Integer,
            nullable=False,
            default=0,
        ),
        sa.Column(
            "findings_summary", postgresql.JSON(), nullable=True
        ),
        sa.Column("raw_data", postgresql.JSON(), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("pdf_path", sa.String(512), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index("ix_scans_domain_id", "scans", ["domain_id"])
    op.create_index("ix_scans_user_id", "scans", ["user_id"])
    op.create_index("ix_scans_status", "scans", ["status"])

    # ── findings ──────────────────────────────────────────
    op.create_table(
        "findings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "scan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column(
            "severity", sa.String(16), nullable=False
        ),
        sa.Column(
            "severity_rank", sa.Integer, nullable=False, default=4
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("evidence", postgresql.JSON(), nullable=False),
        sa.Column("recommendation", sa.Text, nullable=False),
        sa.Column("source_tool", sa.String(64), nullable=False),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer, nullable=True),
        sa.Column("cve", sa.String(32), nullable=True),
        sa.Column("cvss_score", sa.Float, nullable=True),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_findings_scan_id", "findings", ["scan_id"]
    )
    op.create_index(
        "ix_findings_severity", "findings", ["severity"]
    )


def downgrade() -> None:
    op.drop_table("findings")
    op.drop_table("scans")
    op.drop_table("domains")
    op.drop_table("subscriptions")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS scanstatus")
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")
