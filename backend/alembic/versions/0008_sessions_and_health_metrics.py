"""user session tracking and blood pressure/glucose health metrics

Revision ID: 0008_sessions_health_metrics
Revises: 0007_auth_revoke_health
Create Date: 2026-08-24 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "0008_sessions_health_metrics"
down_revision = "0007_auth_revoke_health"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", sa.String(), unique=True, nullable=False),
        sa.Column("device_label", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_session_id", "user_sessions", ["session_id"], unique=True)

    op.add_column("health_metric_records", sa.Column("systolic_bp", sa.Integer(), nullable=True))
    op.add_column("health_metric_records", sa.Column("diastolic_bp", sa.Integer(), nullable=True))
    op.add_column("health_metric_records", sa.Column("blood_glucose", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("health_metric_records", "blood_glucose")
    op.drop_column("health_metric_records", "diastolic_bp")
    op.drop_column("health_metric_records", "systolic_bp")
    op.drop_index("ix_user_sessions_session_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
