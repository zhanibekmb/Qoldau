"""Durable private email and attachment scan provenance.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("attachments", sa.Column("scan_engine", sa.String(20), nullable=True))
    with op.batch_alter_table("email_outbox") as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("attempts", sa.Integer(), server_default="0", nullable=False))
        batch.add_column(sa.Column("next_attempt_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("claim_id", sa.String(32), nullable=True))
        batch.add_column(sa.Column("sent_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("last_error", sa.String(40), nullable=True))
        batch.create_foreign_key("fk_outbox_user", "users", ["user_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_email_outbox_delivery", ["status", "next_attempt_at"])
    # Old rows may contain subjects and excerpts. Never retry them under the new sender.
    op.execute("UPDATE email_outbox SET subject = '', body = '', status = 'logged', last_error = 'legacy_redacted'")


def downgrade() -> None:
    with op.batch_alter_table("email_outbox") as batch:
        batch.drop_index("ix_email_outbox_delivery")
        batch.drop_constraint("fk_outbox_user", type_="foreignkey")
        for column in ("last_error", "sent_at", "claim_id", "next_attempt_at", "attempts", "user_id"):
            batch.drop_column(column)
    op.drop_column("attachments", "scan_engine")
