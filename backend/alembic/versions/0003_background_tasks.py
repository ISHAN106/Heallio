"""background task queue table

Revision ID: 0003_background_tasks
Revises: 0002_security_privacy_tables
Create Date: 2026-04-01 00:20:00

"""

from alembic import op
import sqlalchemy as sa


revision = "0003_background_tasks"
down_revision = "0002_security_privacy_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "background_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_name", sa.String(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("run_at", sa.DateTime(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_background_tasks_id", "background_tasks", ["id"])
    op.create_index("ix_background_tasks_task_name", "background_tasks", ["task_name"])
    op.create_index("ix_background_tasks_status", "background_tasks", ["status"])
    op.create_index("ix_background_tasks_run_at", "background_tasks", ["run_at"])


def downgrade() -> None:
    op.drop_index("ix_background_tasks_run_at", table_name="background_tasks")
    op.drop_index("ix_background_tasks_status", table_name="background_tasks")
    op.drop_index("ix_background_tasks_task_name", table_name="background_tasks")
    op.drop_index("ix_background_tasks_id", table_name="background_tasks")
    op.drop_table("background_tasks")
