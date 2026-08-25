"""token revocation column and health metric records

Revision ID: 0007_auth_revoke_health
Revises: 0006_prescriptions
Create Date: 2026-08-14 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "0007_auth_revoke_health"
down_revision = "0006_prescriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("tokens_valid_from", sa.DateTime(), nullable=True))

    # health_metric_records was historically created ad-hoc at request time via
    # raw SQL, so it may already exist in older databases. Only create it when
    # missing to keep this migration safe on both fresh and existing schemas.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "health_metric_records" not in inspector.get_table_names():
        op.create_table(
            "health_metric_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("steps", sa.Integer(), nullable=True),
            sa.Column("heart_rate", sa.Float(), nullable=True),
            sa.Column("calories_burned", sa.Float(), nullable=True),
            sa.Column("recorded_at", sa.DateTime(), nullable=True),
        )
        op.create_index(
            "ix_health_metric_records_user_id",
            "health_metric_records",
            ["user_id"],
        )


def downgrade() -> None:
    op.drop_column("users", "tokens_valid_from")
    # health_metric_records is left intact: it predates Alembic management.
