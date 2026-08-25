"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-04-01 00:00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password", sa.String(), nullable=False),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "health_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("metric", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_health_records_id", "health_records", ["id"])

    op.create_table(
        "diet_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("meal_type", sa.String(), nullable=False),
        sa.Column("food", sa.String(), nullable=False),
        sa.Column("calories", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_diet_records_id", "diet_records", ["id"])

    op.create_table(
        "sleep_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sleep_start", sa.DateTime(), nullable=False),
        sa.Column("sleep_end", sa.DateTime(), nullable=False),
        sa.Column("quality", sa.String(), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_sleep_records_id", "sleep_records", ["id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("response", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_chat_messages_id", "chat_messages", ["id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_sleep_records_id", table_name="sleep_records")
    op.drop_table("sleep_records")

    op.drop_index("ix_diet_records_id", table_name="diet_records")
    op.drop_table("diet_records")

    op.drop_index("ix_health_records_id", table_name="health_records")
    op.drop_table("health_records")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
