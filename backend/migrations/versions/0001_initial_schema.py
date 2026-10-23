"""Initial schema (issue #26, task 3).

Written by hand against ``vulntriage.db.models`` and frozen: it lists every
table, column and constraint itself, so later model changes need a new
revision (the drift test in ``tests/test_db_migration.py`` enforces that).
Enums are strings with CHECK constraints so Postgres can reuse this file.

Revision ID: 0001
Revises:
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TIERS = ("P1", "P2", "P3", "P4")
STATUSES = ("open", "risk accepted", "fixed", "withdrawn")
SCAN_STATUSES = (
    "not yet scanned", "scan failed", "scanned, findings", "scanned, incomplete",
    "scanned, clean",
)
FAILURE_REASONS = (
    "feed unavailable", "lockfile parse error", "repository unavailable", "no dependency files",
)
ECOSYSTEMS = ("PyPI", "npm")


def _in(table: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    listed = ", ".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(f"{column} IN ({listed})", name=op.f(f"ck_{table}_{column}"))


def _fk(table: str, column: str, target: str, target_column: str = "id") -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.{target_column}"], name=op.f(f"fk_{table}_{column}_{target}")
    )


def _dt() -> sa.DateTime:
    return sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        _in("users", "role", ("security lead", "asset owner")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", _dt(), nullable=False),
        sa.Column("last_seen_at", _dt(), nullable=False),
        sa.Column("expires_at", _dt(), nullable=False),
        _fk("sessions", "user_id", "users"),
    )
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("owner_name", sa.String(), nullable=True),
        sa.Column("owner_email", sa.String(), nullable=True),
        sa.Column("criticality", sa.String(), nullable=False),
        sa.Column("internet_facing", sa.Boolean(), nullable=False),
        sa.Column("repository_url", sa.String(), nullable=False),
        sa.Column("scan_status", sa.String(), nullable=False),
        sa.Column("scan_failure_reason", sa.String(), nullable=True),
        sa.Column("last_scan_at", _dt(), nullable=True),
        sa.Column("last_commit_sha", sa.String(), nullable=True),
        _in("assets", "criticality", ("low", "medium", "high", "critical")),
        _in("assets", "scan_status", SCAN_STATUSES),
        _in("assets", "scan_failure_reason", FAILURE_REASONS),
    )
    op.create_table(
        "scans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.String(), nullable=False),
        sa.Column("started_at", _dt(), nullable=False),
        sa.Column("finished_at", _dt(), nullable=True),
        sa.Column("scan_status", sa.String(), nullable=False),
        sa.Column("failure_reason", sa.String(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("trace_id", sa.String(), nullable=False),
        _fk("scans", "asset_id", "assets"),
        _in("scans", "trigger", ("registration", "schedule", "person")),
        _in("scans", "scan_status", SCAN_STATUSES),
        _in("scans", "failure_reason", FAILURE_REASONS),
    )
    op.create_table(
        "dependencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("ecosystem", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=True),
        sa.Column("source_file", sa.String(), nullable=False),
        sa.Column("direct", sa.Boolean(), nullable=False),
        _fk("dependencies", "asset_id", "assets"),
        _in("dependencies", "ecosystem", ECOSYSTEMS),
    )
    op.create_table(
        "vulnerabilities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("identity_key", sa.String(), nullable=False),
        sa.Column("cve_id", sa.String(), nullable=True),
        sa.UniqueConstraint("identity_key", name=op.f("uq_vulnerabilities_identity_key")),
        sa.UniqueConstraint("cve_id", name=op.f("uq_vulnerabilities_cve_id")),
        sa.CheckConstraint(
            "cve_id IS NULL OR identity_key = cve_id",
            name=op.f("ck_vulnerabilities_identity_key"),
        ),
    )
    op.create_table(
        "advisories",
        sa.Column("osv_id", sa.String(), primary_key=True),
        sa.Column("vulnerability_id", sa.Integer(), nullable=False),
        sa.Column("modified", _dt(), nullable=False),
        sa.Column("withdrawn_at", _dt(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("affected", sa.JSON(), nullable=False),
        sa.Column("references", sa.JSON(), nullable=False),
        _fk("advisories", "vulnerability_id", "vulnerabilities"),
    )
    op.create_table(
        "vulnerability_aliases",
        sa.Column("alias_id", sa.String(), primary_key=True),
        sa.Column("vulnerability_id", sa.Integer(), nullable=False),
        _fk("vulnerability_aliases", "vulnerability_id", "vulnerabilities"),
    )
    op.create_table(
        "signals",
        sa.Column("cve_id", sa.String(), primary_key=True),
        sa.Column("kev_listed", sa.Boolean(), nullable=True),
        sa.Column("kev_date_added", sa.Date(), nullable=True),
        sa.Column("kev_fetched_at", _dt(), nullable=True),
        sa.Column("kev_stale", sa.Boolean(), nullable=False),
        sa.Column("epss_score", sa.Float(), nullable=True),
        sa.Column("epss_percentile", sa.Float(), nullable=True),
        sa.Column("epss_date", sa.Date(), nullable=True),
        sa.Column("epss_fetched_at", _dt(), nullable=True),
        sa.Column("epss_stale", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("vulnerability_id", sa.Integer(), nullable=False),
        sa.Column("ecosystem", sa.String(), nullable=False),
        sa.Column("package", sa.String(), nullable=False),
        sa.Column("fixed_version", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("status_before_withdrawal", sa.String(), nullable=True),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column("rank_inputs", sa.JSON(), nullable=False),
        sa.Column("rank_reason", sa.Text(), nullable=False),
        sa.Column("first_detected_at", _dt(), nullable=False),
        # No foreign key: it would form a cycle with lifecycles.finding_id.
        sa.Column("current_lifecycle_id", sa.Integer(), nullable=True),
        sa.Column("fixed_at", _dt(), nullable=True),
        sa.Column("stale", sa.Boolean(), nullable=False),
        sa.Column("stale_since", _dt(), nullable=True),
        sa.Column("signals_changed", sa.Boolean(), nullable=False),
        _fk("findings", "asset_id", "assets"),
        _fk("findings", "vulnerability_id", "vulnerabilities"),
        sa.UniqueConstraint(
            "asset_id", "ecosystem", "package", "vulnerability_id",
            name=op.f("uq_findings_identity"),
        ),
        _in("findings", "status", STATUSES),
        _in("findings", "status_before_withdrawal", STATUSES),
        _in("findings", "tier", TIERS),
        _in("findings", "ecosystem", ECOSYSTEMS),
    )
    op.create_table(
        "finding_dependencies",
        sa.Column("finding_id", sa.Integer(), primary_key=True),
        sa.Column("dependency_id", sa.Integer(), primary_key=True),
        _fk("finding_dependencies", "finding_id", "findings"),
        _fk("finding_dependencies", "dependency_id", "dependencies"),
    )
    op.create_table(
        "lifecycles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("finding_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("started_at", _dt(), nullable=False),
        sa.Column("due_at", _dt(), nullable=False),
        sa.Column("highest_tier", sa.String(), nullable=False),
        sa.Column("entered_p1_at", _dt(), nullable=True),
        sa.Column("tracker_issue_number", sa.Integer(), nullable=True),
        sa.Column("owner_notified_at", _dt(), nullable=True),
        sa.Column("ended_at", _dt(), nullable=True),
        _fk("lifecycles", "finding_id", "findings"),
        sa.UniqueConstraint("finding_id", "number", name=op.f("uq_lifecycles_finding_number")),
        _in("lifecycles", "highest_tier", TIERS),
    )
    op.create_table(
        "notification_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lifecycle_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("recipient", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sa.String(), nullable=True),
        sa.Column("traceparent", sa.String(), nullable=False),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column("created_at", _dt(), nullable=False),
        sa.Column("sent_at", _dt(), nullable=True),
        _fk("notification_jobs", "lifecycle_id", "lifecycles"),
        sa.UniqueConstraint(
            "idempotency_key", name=op.f("uq_notification_jobs_idempotency_key")
        ),
        _in(
            "notification_jobs", "kind",
            ("top tier", "reminder", "escalation", "signals changed", "issue close", "digest"),
        ),
        _in("notification_jobs", "recipient", ("owner", "security lead")),
        _in(
            "notification_jobs", "state",
            (
                "pending", "claimed", "sent", "failed", "held: ownerless",
                "held: owner email missing", "held: configuration error",
            ),
        ),
        _in("notification_jobs", "tier", TIERS),
    )
    op.create_table(
        "audit_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("finding_id", sa.Integer(), nullable=True),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("field", sa.String(), nullable=False),
        sa.Column("previous_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("restores_entry_id", sa.Integer(), nullable=True),
        sa.Column("created_at", _dt(), nullable=False),
        _fk("audit_entries", "finding_id", "findings"),
        _fk("audit_entries", "asset_id", "assets"),
        _fk("audit_entries", "restores_entry_id", "audit_entries"),
        sa.CheckConstraint(
            "(finding_id IS NOT NULL AND asset_id IS NULL)"
            " OR (finding_id IS NULL AND asset_id IS NOT NULL)",
            name=op.f("ck_audit_entries_one_target"),
        ),
        sa.CheckConstraint(
            "NOT (field = 'status' AND new_value = 'risk accepted'"
            " AND restores_entry_id IS NULL"
            " AND (reason IS NULL OR trim(reason) = ''))",
            name=op.f("ck_audit_entries_risk_accepted_reason"),
        ),
    )


def downgrade() -> None:
    for table in (
        "audit_entries",
        "notification_jobs",
        "lifecycles",
        "finding_dependencies",
        "findings",
        "signals",
        "vulnerability_aliases",
        "advisories",
        "vulnerabilities",
        "dependencies",
        "scans",
        "assets",
        "sessions",
        "users",
    ):
        op.drop_table(table)
