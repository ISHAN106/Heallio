"""doctor consultation flow

Revision ID: 0004_doctor_consultation_flow
Revises: 0003_background_tasks
Create Date: 2026-04-08 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "0004_doctor_consultation_flow"
down_revision = "0003_background_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
    )
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "doctor_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_doctor_categories_id", "doctor_categories", ["id"])
    op.create_index("ix_doctor_categories_name", "doctor_categories", ["name"], unique=True)

    op.create_table(
        "doctor_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("doctor_categories.id"), nullable=False),
        sa.Column("license_number", sa.String(), nullable=False, unique=True),
        sa.Column("years_experience", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bio", sa.String(), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("average_rating", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_ratings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_consultations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_doctor_profiles_id", "doctor_profiles", ["id"])
    op.create_index("ix_doctor_profiles_license_number", "doctor_profiles", ["license_number"], unique=True)

    op.create_table(
        "consultation_tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("trigger_source", sa.String(), nullable=False),
        sa.Column("trigger_reason", sa.Text(), nullable=False),
        sa.Column("severity_score", sa.Integer(), nullable=False),
        sa.Column("severity_level", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_consultation_tickets_id", "consultation_tickets", ["id"])
    op.create_index("ix_consultation_tickets_user_id", "consultation_tickets", ["user_id"])
    op.create_index("ix_consultation_tickets_doctor_id", "consultation_tickets", ["doctor_id"])

    op.create_table(
        "consultation_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("consultation_tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sender_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_consultation_messages_id", "consultation_messages", ["id"])
    op.create_index("ix_consultation_messages_ticket_id", "consultation_messages", ["ticket_id"])
    op.create_index("ix_consultation_messages_sender_user_id", "consultation_messages", ["sender_user_id"])

    op.create_table(
        "doctor_ratings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("consultation_tickets.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_doctor_ratings_id", "doctor_ratings", ["id"])
    op.create_index("ix_doctor_ratings_user_id", "doctor_ratings", ["user_id"])
    op.create_index("ix_doctor_ratings_doctor_id", "doctor_ratings", ["doctor_id"])

    op.execute(
        """
        INSERT INTO doctor_categories (name, description, created_at)
        VALUES
            ('General Physician', 'Primary care and general consultation', CURRENT_TIMESTAMP),
            ('Nutrition', 'Diet, weight management, and metabolic guidance', CURRENT_TIMESTAMP),
            ('Cardiology', 'Heart health and cardiovascular risk management', CURRENT_TIMESTAMP),
            ('Mental Health', 'Stress, anxiety, and emotional wellness support', CURRENT_TIMESTAMP)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_doctor_ratings_doctor_id", table_name="doctor_ratings")
    op.drop_index("ix_doctor_ratings_user_id", table_name="doctor_ratings")
    op.drop_index("ix_doctor_ratings_id", table_name="doctor_ratings")
    op.drop_table("doctor_ratings")

    op.drop_index("ix_consultation_messages_sender_user_id", table_name="consultation_messages")
    op.drop_index("ix_consultation_messages_ticket_id", table_name="consultation_messages")
    op.drop_index("ix_consultation_messages_id", table_name="consultation_messages")
    op.drop_table("consultation_messages")

    op.drop_index("ix_consultation_tickets_doctor_id", table_name="consultation_tickets")
    op.drop_index("ix_consultation_tickets_user_id", table_name="consultation_tickets")
    op.drop_index("ix_consultation_tickets_id", table_name="consultation_tickets")
    op.drop_table("consultation_tickets")

    op.drop_index("ix_doctor_profiles_license_number", table_name="doctor_profiles")
    op.drop_index("ix_doctor_profiles_id", table_name="doctor_profiles")
    op.drop_table("doctor_profiles")

    op.drop_index("ix_doctor_categories_name", table_name="doctor_categories")
    op.drop_index("ix_doctor_categories_id", table_name="doctor_categories")
    op.drop_table("doctor_categories")

    op.drop_column("users", "is_active")
    op.drop_column("users", "role")
