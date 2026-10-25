"""SQLAlchemy models for architecture.md, Data model (task 3, issue #26).

Enums are stored as strings with a CHECK constraint. Every constraint has an
explicit name so the Alembic migration, SQLite batch mode and Postgres agree.
Untrusted text (``summary``, ``details``, ``references``) is only stored here;
nothing renders it. ``Brief`` is not built yet (future-development task 30), and the KEV
value is derived (``enums.kev_value``), not a column.
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from vulntriage.db.enums import (
    Criticality,
    Ecosystem,
    FailureReason,
    FindingStatus,
    NotificationKind,
    NotificationRecipient,
    NotificationState,
    ScanStatus,
    ScanTrigger,
    Tier,
    UserRole,
)


class UtcDateTime(TypeDecorator[dt.datetime]):
    """Timezone-aware UTC datetimes; SQLite drops the zone, so restore it on read."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: dt.datetime | None, dialect: Dialect) -> dt.datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime: use a timezone-aware UTC value")
        return value.astimezone(dt.UTC)

    def process_result_value(self, value: dt.datetime | None, dialect: Dialect) -> dt.datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.UTC)
        return value.astimezone(dt.UTC)


class Base(DeclarativeBase):
    pass


def _check_in(table: str, column: str, enum_cls: type[StrEnum]) -> CheckConstraint:
    values = ", ".join(f"'{member.value}'" for member in enum_cls)
    return CheckConstraint(f"{column} IN ({values})", name=f"ck_{table}_{column}")


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        _check_in("users", "role", UserRole),
        UniqueConstraint("username", name="uq_users_username"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String)
    display_name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    # Plain string: this task hashes nothing (Argon2id is task 9).
    password_hash: Mapped[str] = mapped_column(String)


class AuthSession(Base):
    """A login session (table ``sessions``)."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # hash of the cookie value
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", name="fk_sessions_user_id_users"))
    created_at: Mapped[dt.datetime] = mapped_column(UtcDateTime)
    last_seen_at: Mapped[dt.datetime] = mapped_column(UtcDateTime)
    expires_at: Mapped[dt.datetime] = mapped_column(UtcDateTime)


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        _check_in("assets", "criticality", Criticality),
        _check_in("assets", "scan_status", ScanStatus),
        _check_in("assets", "scan_failure_reason", FailureReason),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    owner_name: Mapped[str | None] = mapped_column(String)
    owner_email: Mapped[str | None] = mapped_column(String)
    criticality: Mapped[str] = mapped_column(String)
    internet_facing: Mapped[bool] = mapped_column(Boolean)
    repository_url: Mapped[str] = mapped_column(String)
    scan_status: Mapped[str] = mapped_column(String, default=ScanStatus.NOT_YET_SCANNED.value)
    scan_failure_reason: Mapped[str | None] = mapped_column(String)
    last_scan_at: Mapped[dt.datetime | None] = mapped_column(UtcDateTime)
    last_commit_sha: Mapped[str | None] = mapped_column(String)


class Scan(Base):
    __tablename__ = "scans"
    __table_args__ = (
        _check_in("scans", "trigger", ScanTrigger),
        _check_in("scans", "scan_status", ScanStatus),
        _check_in("scans", "failure_reason", FailureReason),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", name="fk_scans_asset_id_assets"))
    trigger: Mapped[str] = mapped_column(String)
    started_at: Mapped[dt.datetime] = mapped_column(UtcDateTime)
    finished_at: Mapped[dt.datetime | None] = mapped_column(UtcDateTime)
    scan_status: Mapped[str] = mapped_column(String)
    failure_reason: Mapped[str | None] = mapped_column(String)
    # List of {kind, file, line, message}.
    warnings: Mapped[list[Any]] = mapped_column(JSON, default=list)
    trace_id: Mapped[str] = mapped_column(String)


class Dependency(Base):
    __tablename__ = "dependencies"
    __table_args__ = (_check_in("dependencies", "ecosystem", Ecosystem),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", name="fk_dependencies_asset_id_assets")
    )
    ecosystem: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)  # normalised (VERIFY: PEP 503)
    version: Mapped[str | None] = mapped_column(String)  # null = "version unknown"
    source_file: Mapped[str] = mapped_column(String)
    direct: Mapped[bool] = mapped_column(Boolean)


class Vulnerability(Base):
    __tablename__ = "vulnerabilities"
    __table_args__ = (
        UniqueConstraint("identity_key", name="uq_vulnerabilities_identity_key"),
        UniqueConstraint("cve_id", name="uq_vulnerabilities_cve_id"),
        CheckConstraint(
            "cve_id IS NULL OR identity_key = cve_id", name="ck_vulnerabilities_identity_key"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identity_key: Mapped[str] = mapped_column(String)
    cve_id: Mapped[str | None] = mapped_column(String)


class Advisory(Base):
    __tablename__ = "advisories"

    osv_id: Mapped[str] = mapped_column(String, primary_key=True)
    vulnerability_id: Mapped[int] = mapped_column(
        ForeignKey("vulnerabilities.id", name="fk_advisories_vulnerability_id_vulnerabilities")
    )
    modified: Mapped[dt.datetime] = mapped_column(UtcDateTime)
    withdrawn_at: Mapped[dt.datetime | None] = mapped_column(UtcDateTime)
    # Untrusted text: stored only, never rendered as links.
    summary: Mapped[str] = mapped_column(Text)
    details: Mapped[str] = mapped_column(Text)
    affected: Mapped[list[Any]] = mapped_column(JSON)  # ranges and events
    references: Mapped[list[Any]] = mapped_column(JSON)


class VulnerabilityAlias(Base):
    __tablename__ = "vulnerability_aliases"

    alias_id: Mapped[str] = mapped_column(String, primary_key=True)  # unique by being the key
    vulnerability_id: Mapped[int] = mapped_column(
        ForeignKey(
            "vulnerabilities.id", name="fk_vulnerability_aliases_vulnerability_id_vulnerabilities"
        )
    )


class Signal(Base):
    __tablename__ = "signals"

    cve_id: Mapped[str] = mapped_column(String, primary_key=True)
    kev_listed: Mapped[bool | None] = mapped_column(Boolean)
    kev_date_added: Mapped[dt.date | None] = mapped_column(Date)
    kev_fetched_at: Mapped[dt.datetime | None] = mapped_column(UtcDateTime)
    kev_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    epss_score: Mapped[float | None] = mapped_column(Float)
    epss_percentile: Mapped[float | None] = mapped_column(Float)
    epss_date: Mapped[dt.date | None] = mapped_column(Date)
    epss_fetched_at: Mapped[dt.datetime | None] = mapped_column(UtcDateTime)
    epss_stale: Mapped[bool] = mapped_column(Boolean, default=False)


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint(
            "asset_id", "ecosystem", "package", "vulnerability_id", name="uq_findings_identity"
        ),
        _check_in("findings", "status", FindingStatus),
        _check_in("findings", "status_before_withdrawal", FindingStatus),
        _check_in("findings", "tier", Tier),
        _check_in("findings", "ecosystem", Ecosystem),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", name="fk_findings_asset_id_assets"))
    vulnerability_id: Mapped[int] = mapped_column(
        ForeignKey("vulnerabilities.id", name="fk_findings_vulnerability_id_vulnerabilities")
    )
    ecosystem: Mapped[str] = mapped_column(String)
    package: Mapped[str] = mapped_column(String)
    fixed_version: Mapped[str | None] = mapped_column(String)  # null = "no fixed version"
    status: Mapped[str] = mapped_column(String, default=FindingStatus.OPEN.value)
    status_before_withdrawal: Mapped[str | None] = mapped_column(String)
    tier: Mapped[str] = mapped_column(String)
    rank_inputs: Mapped[dict[str, Any]] = mapped_column(JSON)
    rank_reason: Mapped[str] = mapped_column(Text)
    first_detected_at: Mapped[dt.datetime] = mapped_column(UtcDateTime)
    # Deliberately no foreign key: it would form a cycle with lifecycles.finding_id,
    # and SQLite cannot add a constraint with ALTER. The application keeps it valid.
    current_lifecycle_id: Mapped[int | None] = mapped_column(Integer)
    fixed_at: Mapped[dt.datetime | None] = mapped_column(UtcDateTime)
    stale: Mapped[bool] = mapped_column(Boolean, default=False)
    stale_since: Mapped[dt.datetime | None] = mapped_column(UtcDateTime)
    signals_changed: Mapped[bool] = mapped_column(Boolean, default=False)


class FindingDependency(Base):
    """Link table: a finding links to one or more Dependencies (A6)."""

    __tablename__ = "finding_dependencies"

    finding_id: Mapped[int] = mapped_column(
        ForeignKey("findings.id", name="fk_finding_dependencies_finding_id_findings"),
        primary_key=True,
    )
    dependency_id: Mapped[int] = mapped_column(
        ForeignKey("dependencies.id", name="fk_finding_dependencies_dependency_id_dependencies"),
        primary_key=True,
    )


class Lifecycle(Base):
    __tablename__ = "lifecycles"
    __table_args__ = (
        UniqueConstraint("finding_id", "number", name="uq_lifecycles_finding_number"),
        _check_in("lifecycles", "highest_tier", Tier),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    finding_id: Mapped[int] = mapped_column(
        ForeignKey("findings.id", name="fk_lifecycles_finding_id_findings")
    )
    number: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[dt.datetime] = mapped_column(UtcDateTime)
    due_at: Mapped[dt.datetime] = mapped_column(UtcDateTime)
    highest_tier: Mapped[str] = mapped_column(String)
    entered_p1_at: Mapped[dt.datetime | None] = mapped_column(UtcDateTime)
    tracker_issue_number: Mapped[int | None] = mapped_column(Integer)
    owner_notified_at: Mapped[dt.datetime | None] = mapped_column(UtcDateTime)
    ended_at: Mapped[dt.datetime | None] = mapped_column(UtcDateTime)


class NotificationJob(Base):
    __tablename__ = "notification_jobs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_notification_jobs_idempotency_key"),
        _check_in("notification_jobs", "kind", NotificationKind),
        _check_in("notification_jobs", "recipient", NotificationRecipient),
        _check_in("notification_jobs", "state", NotificationState),
        _check_in("notification_jobs", "tier", Tier),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lifecycle_id: Mapped[int | None] = mapped_column(
        ForeignKey("lifecycles.id", name="fk_notification_jobs_lifecycle_id_lifecycles")
    )  # null for the digest
    kind: Mapped[str] = mapped_column(String)
    recipient: Mapped[str] = mapped_column(String)
    idempotency_key: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String, default=NotificationState.PENDING.value)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String)
    traceparent: Mapped[str] = mapped_column(String)  # set at creation, never null
    tier: Mapped[str] = mapped_column(String)  # the finding's tier at creation; never changes
    created_at: Mapped[dt.datetime] = mapped_column(UtcDateTime, default=_utcnow)
    sent_at: Mapped[dt.datetime | None] = mapped_column(UtcDateTime)


class AuditEntry(Base):
    """Append-only: the ORM refuses updates and deletes (see the guards below)."""

    __tablename__ = "audit_entries"
    __table_args__ = (
        CheckConstraint(
            "(finding_id IS NOT NULL AND asset_id IS NULL)"
            " OR (finding_id IS NULL AND asset_id IS NOT NULL)",
            name="ck_audit_entries_one_target",
        ),
        CheckConstraint(
            "NOT (field = 'status' AND new_value = 'risk accepted'"
            " AND restores_entry_id IS NULL"
            " AND (reason IS NULL OR trim(reason) = ''))",  # trims spaces only; the API (task 8) also refuses tab/newline-only
            name="ck_audit_entries_risk_accepted_reason",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    finding_id: Mapped[int | None] = mapped_column(
        ForeignKey("findings.id", name="fk_audit_entries_finding_id_findings")
    )
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", name="fk_audit_entries_asset_id_assets")
    )
    field: Mapped[str] = mapped_column(String)
    previous_value: Mapped[str | None] = mapped_column(Text)  # none on creation
    new_value: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String)  # user id, "re-scan" or "system"
    source: Mapped[str] = mapped_column(String)
    reason: Mapped[str | None] = mapped_column(Text)
    restores_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("audit_entries.id", name="fk_audit_entries_restores_entry_id_audit_entries")
    )
    created_at: Mapped[dt.datetime] = mapped_column(UtcDateTime, default=_utcnow)


class AppendOnlyError(Exception):
    """Raised when code tries to update or delete an audit entry."""


@event.listens_for(AuditEntry, "before_update")
def _refuse_audit_update(mapper: Any, connection: Any, target: AuditEntry) -> None:
    raise AppendOnlyError("audit entries are append-only: update refused")


@event.listens_for(AuditEntry, "before_delete")
def _refuse_audit_delete(mapper: Any, connection: Any, target: AuditEntry) -> None:
    raise AppendOnlyError("audit entries are append-only: delete refused")
