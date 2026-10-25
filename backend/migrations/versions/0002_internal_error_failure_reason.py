"""Add the fifth failure reason ``internal error`` (issue #198).

Widens the CHECK constraints on ``assets.scan_failure_reason`` and
``scans.failure_reason``. ``0001`` is frozen, so this revision drops and
recreates both constraints (batch mode, so SQLite rebuilds the table and
Postgres alters it in place). The downgrade first rewrites any ``internal error``
row to ``feed unavailable`` so the narrower constraint can be restored; that
loses the reason text of those rows, so it is a development-only convenience.

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

OLD = (
    "feed unavailable", "lockfile parse error", "repository unavailable", "no dependency files",
)
NEW = OLD + ("internal error",)
TARGETS = (("assets", "scan_failure_reason"), ("scans", "failure_reason"))


def _rebuild(values: tuple[str, ...]) -> None:
    listed = ", ".join(f"'{v}'" for v in values)
    for table, column in TARGETS:
        name = f"ck_{table}_{column}"
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(op.f(name), type_="check")
            batch.create_check_constraint(op.f(name), sa.text(f"{column} IN ({listed})"))


def upgrade() -> None:
    _rebuild(NEW)


def downgrade() -> None:
    for table, column in TARGETS:
        op.execute(
            sa.text(f"UPDATE {table} SET {column} = 'feed unavailable' WHERE {column} = 'internal error'")
        )
    _rebuild(OLD)
