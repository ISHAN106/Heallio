"""prescriptions

Revision ID: 0006_prescriptions
Revises: 0005_audit_logs
Create Date: 2026-07-09 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "0006_prescriptions"
down_revision = "0005_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prescriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("consultation_tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("supersedes_id", sa.Integer(), sa.ForeignKey("prescriptions.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_prescriptions_id", "prescriptions", ["id"])
    op.create_index("ix_prescriptions_ticket_id", "prescriptions", ["ticket_id"])
    op.create_index("ix_prescriptions_doctor_id", "prescriptions", ["doctor_id"])
    op.create_index("ix_prescriptions_user_id", "prescriptions", ["user_id"])

    op.create_table(
        "prescription_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "prescription_id",
            sa.Integer(),
            sa.ForeignKey("prescriptions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("medication_name", sa.String(), nullable=False),
        sa.Column("dosage", sa.String(), nullable=True),
        sa.Column("frequency", sa.String(), nullable=True),
        sa.Column("duration", sa.String(), nullable=True),
        sa.Column("instructions", sa.String(), nullable=True),
    )
    op.create_index("ix_prescription_items_id", "prescription_items", ["id"])
    op.create_index("ix_prescription_items_prescription_id", "prescription_items", ["prescription_id"])


def downgrade() -> None:
    op.drop_index("ix_prescription_items_prescription_id", table_name="prescription_items")
    op.drop_index("ix_prescription_items_id", table_name="prescription_items")
    op.drop_table("prescription_items")

    op.drop_index("ix_prescriptions_user_id", table_name="prescriptions")
    op.drop_index("ix_prescriptions_doctor_id", table_name="prescriptions")
    op.drop_index("ix_prescriptions_ticket_id", table_name="prescriptions")
    op.drop_index("ix_prescriptions_id", table_name="prescriptions")
    op.drop_table("prescriptions")
