"""Prueba gratuita: columna trial_ends_at en subscriptions.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-05 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column(
            "trial_ends_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    # El beat de expiración filtra por (plan, trial_ends_at); con el
    # índice parcial sólo se recorren las suscripciones en prueba.
    op.create_index(
        "ix_subscriptions_trial_ends_at",
        "subscriptions",
        ["trial_ends_at"],
        postgresql_where=sa.text("trial_ends_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_subscriptions_trial_ends_at",
        table_name="subscriptions",
    )
    op.drop_column("subscriptions", "trial_ends_at")
