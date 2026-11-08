"""Registro de autorización de escaneo en domains.

Guarda la declaración explícita de propiedad del dominio (cuándo,
desde qué IP y con qué user-agent). Es la evidencia de consentimiento
que respalda cada escaneo.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-05 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "domains",
        sa.Column(
            "authorized_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "domains",
        sa.Column("authorized_ip", sa.String(45), nullable=True),
    )
    op.add_column(
        "domains",
        sa.Column(
            "authorized_user_agent", sa.String(512), nullable=True
        ),
    )

    # Los dominios que ya existían se dan por autorizados en el
    # momento de su alta: es lo más fiel que se puede reconstruir, y
    # dejarlos en NULL los haría indistinguibles de un alta sin
    # consentimiento.
    op.execute(
        "UPDATE domains SET authorized_at = created_at "
        "WHERE authorized_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("domains", "authorized_user_agent")
    op.drop_column("domains", "authorized_ip")
    op.drop_column("domains", "authorized_at")
