"""security and privacy tables

Revision ID: 0002_security_privacy_tables
Revises: 0001_initial_schema
Create Date: 2026-04-01 00:10:00

"""

from alembic import op
import sqlalchemy as sa


revision = "0002_security_privacy_tables"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refresh_token_revocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("jti", sa.String(), nullable=False, unique=True),
        sa.Column("user_email", sa.String(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_refresh_token_revocations_id", "refresh_token_revocations", ["id"]
    )
    op.create_index(
        "ix_refresh_token_revocations_jti", "refresh_token_revocations", ["jti"], unique=True
    )
    op.create_index(
        "ix_refresh_token_revocations_user_email",
        "refresh_token_revocations",
        ["user_email"],
        unique=False,
    )

    op.create_table(
        "user_consents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("consent_given", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consent_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("granted_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_user_consents_id", "user_consents", ["id"])

    op.create_table(
        "data_deletion_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_data_deletion_requests_id", "data_deletion_requests", ["id"])
    op.create_index(
        "ix_data_deletion_requests_user_id", "data_deletion_requests", ["user_id"]
    )
    op.create_index(
        "ix_data_deletion_requests_status", "data_deletion_requests", ["status"]
    )


def downgrade() -> None:
    op.drop_index("ix_data_deletion_requests_status", table_name="data_deletion_requests")
    op.drop_index("ix_data_deletion_requests_user_id", table_name="data_deletion_requests")
    op.drop_index("ix_data_deletion_requests_id", table_name="data_deletion_requests")
    op.drop_table("data_deletion_requests")

    op.drop_index("ix_user_consents_id", table_name="user_consents")
    op.drop_table("user_consents")

    op.drop_index(
        "ix_refresh_token_revocations_user_email", table_name="refresh_token_revocations"
    )
    op.drop_index("ix_refresh_token_revocations_jti", table_name="refresh_token_revocations")
    op.drop_index("ix_refresh_token_revocations_id", table_name="refresh_token_revocations")
    op.drop_table("refresh_token_revocations")
