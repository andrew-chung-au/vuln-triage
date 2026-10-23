"""Issue #26 (task 3): data model, enums, constraints and audit trail.

Cases U-SCHEMA, U-ENUM, U-CONSTRAINT and U-AUDIT on in-memory SQLite with the
tables made from the models. The Alembic migration is tested in
``test_db_migration.py``.
"""

from __future__ import annotations

import datetime as dt
import importlib
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vulntriage.db import enums
from vulntriage.db.identity import identity_key
from vulntriage.db.models import (
    Advisory,
    AppendOnlyError,
    Asset,
    AuditEntry,
    AuthSession,
    Base,
    Dependency,
    Finding,
    Lifecycle,
    NotificationJob,
    Scan,
    Signal,
    User,
    Vulnerability,
    VulnerabilityAlias,
)

NOW = dt.datetime(2026, 10, 23, 9, 30, tzinfo=dt.UTC)

EXPECTED_COLUMNS: dict[str, tuple[set[str], set[str]]] = {
    # table: (all columns, nullable columns)
    "users": ({"id", "username", "display_name", "email", "role", "password_hash"}, set()),
    "sessions": ({"id", "user_id", "created_at", "last_seen_at", "expires_at"}, set()),
    "assets": (
        {
            "id", "name", "owner_name", "owner_email", "criticality", "internet_facing",
            "repository_url", "scan_status", "scan_failure_reason", "last_scan_at",
            "last_commit_sha",
        },
        {"owner_name", "owner_email", "scan_failure_reason", "last_scan_at", "last_commit_sha"},
    ),
    "scans": (
        {
            "id", "asset_id", "trigger", "started_at", "finished_at", "scan_status",
            "failure_reason", "warnings", "trace_id",
        },
        {"finished_at", "failure_reason"},
    ),
    "dependencies": (
        {"id", "asset_id", "ecosystem", "name", "version", "source_file", "direct"},
        {"version"},
    ),
    "vulnerabilities": ({"id", "identity_key", "cve_id"}, {"cve_id"}),
    "advisories": (
        {
            "osv_id", "vulnerability_id", "modified", "withdrawn_at", "summary", "details",
            "affected", "references",
        },
        {"withdrawn_at"},
    ),
    "vulnerability_aliases": ({"alias_id", "vulnerability_id"}, set()),
    "signals": (
        {
            "cve_id", "kev_listed", "kev_date_added", "kev_fetched_at", "kev_stale",
            "epss_score", "epss_percentile", "epss_date", "epss_fetched_at", "epss_stale",
        },
        {
            "kev_listed", "kev_date_added", "kev_fetched_at", "epss_score", "epss_percentile",
            "epss_date", "epss_fetched_at",
        },
    ),
    "findings": (
        {
            "id", "asset_id", "vulnerability_id", "ecosystem", "package", "fixed_version",
            "status", "status_before_withdrawal", "tier", "rank_inputs", "rank_reason",
            "first_detected_at", "current_lifecycle_id", "fixed_at", "stale", "stale_since",
            "signals_changed",
        },
        {
            "fixed_version", "status_before_withdrawal", "current_lifecycle_id", "fixed_at",
            "stale_since",
        },
    ),
    "finding_dependencies": ({"finding_id", "dependency_id"}, set()),
    "lifecycles": (
        {
            "id", "finding_id", "number", "started_at", "due_at", "highest_tier",
            "entered_p1_at", "tracker_issue_number", "owner_notified_at", "ended_at",
        },
        {"entered_p1_at", "tracker_issue_number", "owner_notified_at", "ended_at"},
    ),
    "notification_jobs": (
        {
            "id", "lifecycle_id", "kind", "recipient", "idempotency_key", "state", "attempts",
            "last_error_code", "traceparent", "tier", "created_at", "sent_at",
        },
        {"lifecycle_id", "last_error_code", "sent_at"},
    ),
    "audit_entries": (
        {
            "id", "finding_id", "asset_id", "field", "previous_value", "new_value", "actor",
            "source", "reason", "restores_entry_id", "created_at",
        },
        {"finding_id", "asset_id", "previous_value", "reason", "restores_entry_id"},
    ),
}


@pytest.fixture()
def db(sqlite_engine: Engine, sqlite_session: Session) -> Session:
    Base.metadata.create_all(sqlite_engine)
    return sqlite_session


def make_asset(**overrides: Any) -> Asset:
    values: dict[str, Any] = dict(
        name="payments", owner_name="Ada", owner_email="ada@example.test", criticality="high",
        internet_facing=True, repository_url="https://github.com/acme/payments",
    )
    values.update(overrides)
    return Asset(**values)


def make_vuln(**overrides: Any) -> Vulnerability:
    values: dict[str, Any] = dict(identity_key="CVE-2024-0001", cve_id="CVE-2024-0001")
    values.update(overrides)
    return Vulnerability(**values)


def make_finding(asset_id: int, vulnerability_id: int, **overrides: Any) -> Finding:
    values: dict[str, Any] = dict(
        asset_id=asset_id, vulnerability_id=vulnerability_id, ecosystem="PyPI", package="django",
        tier="P2", rank_inputs={"kev": False}, rank_reason="EPSS high", first_detected_at=NOW,
    )
    values.update(overrides)
    return Finding(**values)


def seed_finding(db: Session) -> Finding:
    asset, vuln = make_asset(), make_vuln()
    db.add_all([asset, vuln])
    db.flush()
    finding = make_finding(asset.id, vuln.id)
    db.add(finding)
    db.commit()  # committed, so a later refused insert's rollback keeps these rows
    return finding


def assert_refused(db: Session, *rows: Any) -> None:
    db.add_all(rows)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# --- U-SCHEMA -------------------------------------------------------------


@pytest.mark.unit
def test_tables_match_the_data_model(sqlite_engine: Engine) -> None:
    Base.metadata.create_all(sqlite_engine)
    assert set(inspect(sqlite_engine).get_table_names()) == set(EXPECTED_COLUMNS)
    assert "briefs" not in EXPECTED_COLUMNS  # Brief is task 30


@pytest.mark.unit
@pytest.mark.parametrize("table", sorted(EXPECTED_COLUMNS))
def test_columns_and_nullability(sqlite_engine: Engine, table: str) -> None:
    Base.metadata.create_all(sqlite_engine)
    columns = {c["name"]: c for c in inspect(sqlite_engine).get_columns(table)}
    names, nullable = EXPECTED_COLUMNS[table]
    assert set(columns) == names
    assert {n for n, c in columns.items() if c["nullable"]} - {"id"} >= nullable
    pks = set(inspect(sqlite_engine).get_pk_constraint(table)["constrained_columns"])
    not_null = {n for n, c in columns.items() if not c["nullable"]} | pks
    assert not_null == names - nullable


@pytest.mark.unit
def test_json_columns_round_trip_nested_values(db: Session) -> None:
    finding = seed_finding(db)
    nested = {"kev": True, "epss": [0.1, {"date": "2026-10-23"}], "none": None}
    finding.rank_inputs = nested
    db.add(
        Advisory(
            osv_id="GHSA-aaaa", vulnerability_id=finding.vulnerability_id, modified=NOW,
            summary="s", details="d",
            affected=[{"ranges": [{"events": [{"introduced": "0"}, {"fixed": "1.2.5"}]}]}],
            references=[{"type": "WEB", "url": "https://example.test/<script>"}],
        )
    )
    db.commit()
    db.expire_all()
    assert db.get(Finding, finding.id).rank_inputs == nested
    advisory = db.get(Advisory, "GHSA-aaaa")
    assert advisory.affected[0]["ranges"][0]["events"][1] == {"fixed": "1.2.5"}
    assert advisory.references[0]["url"] == "https://example.test/<script>"


@pytest.mark.unit
def test_datetimes_come_back_utc_aware_and_naive_is_refused(db: Session) -> None:
    asset = make_asset(last_scan_at=NOW)
    db.add(asset)
    db.commit()
    db.expire_all()
    assert db.get(Asset, asset.id).last_scan_at == NOW
    assert db.get(Asset, asset.id).last_scan_at.tzinfo is not None
    db.add(make_asset(name="naive", last_scan_at=dt.datetime(2026, 1, 1)))
    with pytest.raises(Exception, match="naive datetime"):
        db.flush()
    db.rollback()


@pytest.mark.unit
def test_user_password_hash_is_a_plain_string_column(sqlite_engine: Engine) -> None:
    Base.metadata.create_all(sqlite_engine)
    column = {c["name"]: c for c in inspect(sqlite_engine).get_columns("users")}["password_hash"]
    assert str(column["type"]).upper().startswith("VARCHAR")


@pytest.mark.unit
def test_importing_the_app_opens_no_database() -> None:
    import vulntriage.main

    importlib.reload(vulntriage.main)  # would raise or create a file if it opened one


# --- U-ENUM ---------------------------------------------------------------


@pytest.mark.unit
def test_enum_values_are_exactly_the_data_model() -> None:
    def values(cls: type) -> list[str]:
        return [m.value for m in cls]

    assert values(enums.FindingStatus) == ["open", "risk accepted", "fixed", "withdrawn"]
    assert values(enums.ScanStatus) == [
        "not yet scanned", "scan failed", "scanned, findings", "scanned, incomplete",
        "scanned, clean",
    ]
    assert values(enums.FailureReason) == [
        "feed unavailable", "lockfile parse error", "repository unavailable",
        "no dependency files",
    ]
    assert values(enums.KevValue) == ["KEV: listed", "KEV: not listed", "KEV: n/a (no CVE)"]
    assert values(enums.Tier) == ["P1", "P2", "P3", "P4"]
    assert values(enums.Criticality) == ["low", "medium", "high", "critical"]
    assert values(enums.Ecosystem) == ["PyPI", "npm"]
    assert values(enums.UserRole) == ["security lead", "asset owner"]
    assert values(enums.ScanTrigger) == ["registration", "schedule", "person"]
    assert values(enums.NotificationKind) == [
        "top tier", "reminder", "escalation", "signals changed", "issue close", "digest",
    ]
    assert values(enums.NotificationRecipient) == ["owner", "security lead"]
    assert values(enums.NotificationState) == [
        "pending", "claimed", "sent", "failed", "held: ownerless", "held: owner email missing",
        "held: configuration error",
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("cve_id", "kev_listed", "expected"),
    [
        (None, None, "KEV: n/a (no CVE)"),
        (None, True, "KEV: n/a (no CVE)"),
        ("CVE-2024-1", True, "KEV: listed"),
        ("CVE-2024-1", False, "KEV: not listed"),
        ("CVE-2024-1", None, "KEV: not listed"),  # no successful fetch yet (I15)
    ],
)
def test_kev_value_is_derived(cve_id: str | None, kev_listed: bool | None, expected: str) -> None:
    assert enums.kev_value(cve_id, kev_listed) == expected


@pytest.mark.unit
def test_kev_is_not_a_stored_column() -> None:
    for table in Base.metadata.tables.values():
        assert not any("kev_value" in c.name for c in table.columns)


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_value",
    ["scanned_clean", "Open", "P5", "urgent"],
)
def test_enum_columns_refuse_values_outside_the_list(db: Session, bad_value: str) -> None:
    """Each enum column refuses a value outside its list (the issue's four examples
    are tried against every column; none of them is valid anywhere)."""
    asset = make_asset()
    vuln = make_vuln()
    db.add_all([asset, vuln])
    db.commit()
    user_ok = dict(username="u", display_name="U", email="u@example.test", password_hash="x")
    ts = dict(started_at=NOW, trace_id="t")
    cases: list[Any] = [
        User(role=bad_value, **user_ok),
        make_asset(name="a2", criticality=bad_value),
        make_asset(name="a3", scan_status=bad_value),
        make_asset(name="a4", scan_failure_reason=bad_value),
        Dependency(asset_id=asset.id, ecosystem=bad_value, name="n", source_file="f", direct=True),
        make_finding(asset.id, vuln.id, status=bad_value),
        make_finding(asset.id, vuln.id, status_before_withdrawal=bad_value),
        make_finding(asset.id, vuln.id, tier=bad_value),
        make_finding(asset.id, vuln.id, ecosystem=bad_value),
        _scan(asset.id, trigger=bad_value, **ts),
        _scan(asset.id, scan_status=bad_value, **ts),
        _scan(asset.id, failure_reason=bad_value, **ts),
    ]
    for row in cases:
        assert_refused(db, row)
    finding = make_finding(asset.id, vuln.id)
    db.add(finding)
    db.commit()
    lifecycle_ok = dict(finding_id=finding.id, number=1, started_at=NOW, due_at=NOW)
    assert_refused(db, Lifecycle(highest_tier=bad_value, **lifecycle_ok))
    job_ok = dict(
        kind="top tier", recipient="owner", idempotency_key="k", traceparent="00-x", tier="P1"
    )
    for column in ("kind", "recipient", "state", "tier"):
        assert_refused(db, NotificationJob(**{**job_ok, column: bad_value}))


def _scan(asset_id: int, **overrides: Any) -> Scan:
    values: dict[str, Any] = dict(
        asset_id=asset_id, trigger="person", scan_status="scanned, clean", warnings=[],
    )
    values.update(overrides)
    return Scan(**values)


@pytest.mark.unit
def test_every_listed_enum_value_is_accepted(db: Session) -> None:
    for i, status in enumerate(enums.ScanStatus):
        db.add(make_asset(name=f"a{i}", scan_status=status.value))
    for i, kind in enumerate(enums.NotificationKind):
        for j, state in enumerate(enums.NotificationState):
            db.add(
                NotificationJob(
                    kind=kind.value, recipient="owner", state=state.value, tier="P1",
                    idempotency_key=f"{i}-{j}", traceparent="00-x",
                )
            )
    db.commit()


# --- U-CONSTRAINT ---------------------------------------------------------


@pytest.mark.unit
def test_identity_key_prefers_the_cve() -> None:
    assert identity_key("CVE-2024-1", "GHSA-xxxx") == "CVE-2024-1"
    assert identity_key(None, "GHSA-xxxx") == "GHSA-xxxx"
    # PYSEC and GHSA aliases of one CVE share a key
    assert identity_key("CVE-2024-1", "PYSEC-2024-9") == identity_key("CVE-2024-1", "GHSA-xxxx")


@pytest.mark.unit
def test_identity_key_must_equal_the_cve_when_present(db: Session) -> None:
    assert_refused(db, Vulnerability(cve_id="CVE-2024-1", identity_key="GHSA-xxxx"))
    db.add_all([Vulnerability(cve_id=None, identity_key="GHSA-xxxx"), make_vuln()])
    db.commit()


@pytest.mark.unit
def test_vulnerability_uniqueness(db: Session) -> None:
    db.add(make_vuln())
    db.commit()
    assert_refused(db, make_vuln())  # identity_key and cve_id duplicate
    assert_refused(db, Vulnerability(identity_key="X-other", cve_id="CVE-2024-0001"))
    db.add_all(
        [
            Vulnerability(identity_key="GHSA-1", cve_id=None),
            Vulnerability(identity_key="GHSA-2", cve_id=None),  # several NULL cve_ids allowed
        ]
    )
    db.commit()


@pytest.mark.unit
def test_duplicate_finding_refused_and_one_row_remains(db: Session) -> None:
    finding = seed_finding(db)
    db.commit()
    assert_refused(db, make_finding(finding.asset_id, finding.vulnerability_id))
    assert db.query(Finding).count() == 1


@pytest.mark.unit
@pytest.mark.parametrize("field", ["asset_id", "ecosystem", "package", "vulnerability_id"])
def test_finding_differing_in_one_field_is_accepted(db: Session, field: str) -> None:
    finding = seed_finding(db)
    other_asset = make_asset(name="other")
    other_vuln = make_vuln(identity_key="CVE-2024-0002", cve_id="CVE-2024-0002")
    db.add_all([other_asset, other_vuln])
    db.flush()
    changed = {
        "asset_id": other_asset.id,
        "ecosystem": "npm",
        "package": "flask",
        "vulnerability_id": other_vuln.id,
    }[field]
    keys = {"asset_id": finding.asset_id, "vulnerability_id": finding.vulnerability_id}
    keys.update({k: v for k, v in {field: changed}.items() if k in keys})
    extra = {k: v for k, v in {field: changed}.items() if k not in keys}
    db.add(make_finding(keys["asset_id"], keys["vulnerability_id"], **extra))
    db.commit()
    assert db.query(Finding).count() == 2


@pytest.mark.unit
def test_foreign_keys_are_enforced(db: Session) -> None:
    assert db.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
    vuln = make_vuln()
    db.add(vuln)
    db.commit()
    assert_refused(db, make_finding(asset_id=999, vulnerability_id=vuln.id))
    assert_refused(
        db,
        AuthSession(id="h", user_id=999, created_at=NOW, last_seen_at=NOW, expires_at=NOW),
    )
    assert_refused(db, VulnerabilityAlias(alias_id="GHSA-1", vulnerability_id=999))
    assert_refused(
        db,
        Advisory(
            osv_id="GHSA-1", vulnerability_id=999, modified=NOW, summary="", details="",
            affected=[], references=[],
        ),
    )


@pytest.mark.unit
def test_session_primary_key_and_alias_and_advisory_keys(db: Session) -> None:
    user = User(username="u", display_name="U", email="u@e.test", role="asset owner",
                password_hash="x")
    vuln = make_vuln()
    db.add_all([user, vuln])
    db.flush()
    db.add(AuthSession(id="h1", user_id=user.id, created_at=NOW, last_seen_at=NOW, expires_at=NOW))
    db.add(VulnerabilityAlias(alias_id="GHSA-1", vulnerability_id=vuln.id))
    db.add(
        Advisory(osv_id="GHSA-1", vulnerability_id=vuln.id, modified=NOW, summary="", details="",
                 affected=[], references=[])
    )
    db.add(Signal(cve_id="CVE-2024-0001"))
    db.commit()
    assert_refused(
        db,
        AuthSession(id="h1", user_id=user.id, created_at=NOW, last_seen_at=NOW, expires_at=NOW),
    )
    assert_refused(db, VulnerabilityAlias(alias_id="GHSA-1", vulnerability_id=vuln.id))
    assert_refused(
        db,
        Advisory(osv_id="GHSA-1", vulnerability_id=vuln.id, modified=NOW, summary="", details="",
                 affected=[], references=[]),
    )
    assert_refused(db, Signal(cve_id="CVE-2024-0001"))


@pytest.mark.unit
def test_lifecycle_number_unique_per_finding(db: Session) -> None:
    finding = seed_finding(db)
    row = dict(finding_id=finding.id, number=1, started_at=NOW, due_at=NOW, highest_tier="P2")
    db.add(Lifecycle(**row))
    db.commit()
    assert_refused(db, Lifecycle(**row))
    db.add(Lifecycle(**{**row, "number": 2}))
    db.commit()


@pytest.mark.unit
def test_notification_job_constraints(db: Session) -> None:
    row: dict[str, Any] = dict(
        kind="top tier", recipient="owner", idempotency_key="k1", traceparent="00-x", tier="P1"
    )
    db.add(NotificationJob(**row))
    db.commit()
    assert_refused(db, NotificationJob(**row))  # idempotency_key unique
    assert_refused(db, NotificationJob(**{**row, "idempotency_key": "k2", "traceparent": None}))
    assert_refused(db, NotificationJob(**{**row, "idempotency_key": "k3", "tier": None}))
    stored = db.query(NotificationJob).one()
    assert stored.state == "pending" and stored.attempts == 0


# --- U-AUDIT --------------------------------------------------------------


@pytest.mark.unit
def test_audit_entry_round_trip_and_asset_level_entry(db: Session) -> None:
    finding = seed_finding(db)
    created = AuditEntry(
        finding_id=finding.id, field="status", previous_value=None, new_value="open",
        actor="re-scan", source="OSV", reason=None, created_at=NOW,
    )
    db.add(created)
    db.flush()
    changed = AuditEntry(
        finding_id=finding.id, field="status", previous_value="open", new_value="fixed",
        actor="1", source="dashboard", reason="patched", restores_entry_id=created.id,
        created_at=NOW + dt.timedelta(hours=1),
    )
    asset_entry = AuditEntry(
        asset_id=finding.asset_id, field="criticality", previous_value="high",
        new_value="critical", actor="1", source="dashboard", created_at=NOW,
    )
    db.add_all([changed, asset_entry])
    db.commit()
    db.expire_all()
    first = db.get(AuditEntry, created.id)
    assert (first.actor, first.created_at, first.previous_value, first.new_value) == (
        "re-scan", NOW, None, "open",
    )
    assert (first.source, first.reason, first.restores_entry_id) == ("OSV", None, None)
    second = db.get(AuditEntry, changed.id)
    assert second.previous_value == "open" and second.restores_entry_id == created.id
    assert second.reason == "patched"
    asset_level = db.get(AuditEntry, asset_entry.id)
    assert asset_level.asset_id == finding.asset_id and asset_level.finding_id is None


@pytest.mark.unit
def test_audit_entry_needs_exactly_one_target(db: Session) -> None:
    finding = seed_finding(db)
    base: dict[str, Any] = dict(field="status", new_value="open", actor="system", source="OSV")
    assert_refused(db, AuditEntry(**base))
    assert_refused(db, AuditEntry(finding_id=finding.id, asset_id=finding.asset_id, **base))
    assert_refused(db, AuditEntry(finding_id=finding.id, restores_entry_id=999, **base))


@pytest.mark.unit
@pytest.mark.parametrize("reason", [None, "", "   "])
def test_risk_accepted_needs_a_reason(db: Session, reason: str | None) -> None:
    finding = seed_finding(db)
    row: dict[str, Any] = dict(
        finding_id=finding.id, field="status", previous_value="open", new_value="risk accepted",
        actor="1", source="dashboard",
    )
    assert_refused(db, AuditEntry(reason=reason, **row))
    db.add(AuditEntry(reason="accepted by lead", **row))
    db.commit()


@pytest.mark.unit
def test_risk_accepted_restore_needs_no_reason(db: Session) -> None:
    finding = seed_finding(db)
    original = AuditEntry(
        finding_id=finding.id, field="status", previous_value="open", new_value="withdrawn",
        actor="system", source="OSV",
    )
    db.add(original)
    db.flush()
    db.add(
        AuditEntry(
            finding_id=finding.id, field="status", previous_value="withdrawn",
            new_value="risk accepted", actor="system", source="OSV", reason=None,
            restores_entry_id=original.id,
        )
    )
    db.commit()


@pytest.mark.unit
def test_audit_entries_are_append_only(db: Session) -> None:
    finding = seed_finding(db)
    entry = AuditEntry(
        finding_id=finding.id, field="status", new_value="open", actor="system", source="OSV",
        created_at=NOW,
    )
    db.add(entry)
    db.commit()
    entry_id = entry.id

    entry.new_value = "fixed"
    with pytest.raises(AppendOnlyError):
        db.flush()
    db.rollback()
    assert db.get(AuditEntry, entry_id).new_value == "open"

    db.delete(db.get(AuditEntry, entry_id))
    with pytest.raises(AppendOnlyError):
        db.flush()
    db.rollback()
    assert db.query(AuditEntry).count() == 1
    assert db.get(AuditEntry, entry_id).new_value == "open"
