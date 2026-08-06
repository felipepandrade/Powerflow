"""Add transactional deduplication and idempotent evidence constraints.

Revision ID: 6f4c9b2a1d30
Revises: d07c490192c5
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "6f4c9b2a1d30"
down_revision: str | None = "d07c490192c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("source_items") as batch_op:
        batch_op.create_unique_constraint(
            "uq_source_kind_external_revision",
            ["kind", "external_id", "revision_hash"],
        )
    with op.batch_alter_table("task_evidences") as batch_op:
        batch_op.create_unique_constraint(
            "uq_task_evidence_source_quote",
            ["task_id", "source_item_id", "quote"],
        )


def downgrade() -> None:
    with op.batch_alter_table("task_evidences") as batch_op:
        batch_op.drop_constraint("uq_task_evidence_source_quote", type_="unique")
    with op.batch_alter_table("source_items") as batch_op:
        batch_op.drop_constraint("uq_source_kind_external_revision", type_="unique")
