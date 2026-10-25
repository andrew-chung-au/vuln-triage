"""The operator user-creation command (task 9 defect #176).

Covers task 9's check — "a user created by the command signing in while the
stored password value is an Argon2id hash and not the password" — plus the
non-interactive (piped-stdin) and interactive (tty) password paths, role
validation, duplicate rejection, and that the password is never a command-line
argument. All under `make test` (SQLite, no Docker, no network).
"""

from __future__ import annotations

import io

import pytest
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.api.security import verify_password
from vulntriage.db.enums import NotificationState, Tier
from vulntriage.db.models import Base, NotificationJob, User
from vulntriage.manage import (
    AlertSeedError,
    UserCreationError,
    build_parser,
    clear_alert_seed,
    create_user,
    read_password,
    rescore_finding,
    seed_alert_job,
    set_alert_job,
)
from vulntriage.observability import metrics

# No module-level pytestmark: the read_password/parser cases are `unit`; the
# create_user DB cases are `sqlite_integration`. Each is marked explicitly so no
# case carries both markers.

_PASSWORD = "correct horse battery staple"


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


# -- the password-reading seam (both paths, no real tty needed) ----------------


@pytest.mark.unit
def test_read_password_from_stdin_when_no_terminal() -> None:
    # Piped input (Compose/CI): one line on stdin, newline stripped.
    stdin = io.StringIO(_PASSWORD + "\n")
    got = read_password(stdin=stdin, isatty=lambda: False)
    assert got == _PASSWORD


@pytest.mark.unit
def test_read_password_prompts_when_terminal_attached() -> None:
    # tty: getpass is used (injected), stdin is not read.
    prompts: list[str] = []

    def fake_getpass(prompt: str) -> str:
        prompts.append(prompt)
        return _PASSWORD

    got = read_password(stdin=io.StringIO(""), isatty=lambda: True, getpass_fn=fake_getpass)
    assert got == _PASSWORD
    assert prompts, "getpass was not called in the tty path"


@pytest.mark.unit
def test_read_password_empty_stdin_errors() -> None:
    with pytest.raises(UserCreationError):
        read_password(stdin=io.StringIO(""), isatty=lambda: False)  # EOF, no terminal
    with pytest.raises(UserCreationError):
        read_password(stdin=io.StringIO("\n"), isatty=lambda: False)  # empty line


# -- the command never accepts a password on the command line ------------------


@pytest.mark.unit
def test_create_user_parser_has_no_password_argument() -> None:
    parser = build_parser()
    # --password must not be a recognised option (password is never on argv).
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["create-user", "--username", "u", "--display-name", "D",
             "--email", "e@x", "--role", "security lead", "--password", "x"]
        )


@pytest.mark.unit
def test_create_user_parser_rejects_unknown_role() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["create-user", "--username", "u", "--display-name", "D",
             "--email", "e@x", "--role", "admin"]
        )


# -- create_user: the Argon2id hash + sign-in (task 9's check) -----------------


@pytest.mark.sqlite_integration
def test_create_user_stores_argon2_hash_not_the_password(factory) -> None:  # type: ignore[no-untyped-def]
    user_id = create_user(
        factory, username="lead", display_name="Lead", email="lead@x",
        role="security lead", password=_PASSWORD,
    )
    with factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        # The stored value is an Argon2id hash, never the plaintext.
        assert user.password_hash != _PASSWORD
        assert user.password_hash.startswith("$argon2id$"), user.password_hash
        # And it verifies the password (so the created user can sign in).
        assert verify_password(user.password_hash, _PASSWORD) is True
        assert user.role == "security lead"


@pytest.mark.sqlite_integration
def test_create_user_rejects_unknown_role(factory) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(UserCreationError):
        create_user(
            factory, username="u", display_name="D", email="e@x",
            role="admin", password=_PASSWORD,
        )


@pytest.mark.sqlite_integration
def test_create_user_rejects_duplicate_username(factory) -> None:  # type: ignore[no-untyped-def]
    create_user(
        factory, username="dup", display_name="D", email="e@x",
        role="asset owner", password=_PASSWORD,
    )
    with pytest.raises(UserCreationError):
        create_user(
            factory, username="dup", display_name="D2", email="e2@x",
            role="asset owner", password=_PASSWORD,
        )


# -- the alert firing-state seam (task 27, #159) ------------------------------
# These run the SAME `compute_overdue_series` the overdue gauge reads at
# collection time, so they prove the seam puts a job into the stored state that
# makes the metric read 0/1 as the alert cases expect — the firing comes from
# STORED job state, not an in-test simulation. SQLite + fake clock, no Docker.

import datetime as dt


def _series(factory, now: dt.datetime):  # type: ignore[no-untyped-def]
    with factory() as session:
        return metrics.compute_overdue_series(session, now)


@pytest.mark.sqlite_integration
def test_alert_seed_failed_job_reads_one(factory) -> None:  # type: ignore[no-untyped-def]
    job_id, finding_id = seed_alert_job(factory, state=NotificationState.FAILED.value)
    series = _series(factory, dt.datetime(2026, 1, 1, tzinfo=dt.UTC))
    # Exactly the seeded finding, value 1, tier recorded as P1 (A-FIRE).
    assert len(series) == 1
    fid, tier, value = series[0]
    assert fid == finding_id and tier == Tier.P1.value and value == 1
    assert job_id > 0


@pytest.mark.sqlite_integration
def test_alert_seed_pending_backdated_past_window_reads_one(factory) -> None:  # type: ignore[no-untyped-def]
    # created_at backdated 31 min: past W (30 min) without waiting (A33).
    _job, finding_id = seed_alert_job(
        factory, state=NotificationState.PENDING.value, age_minutes=31
    )
    series = _series(factory, metrics._now())
    assert len(series) == 1 and series[0][0] == finding_id and series[0][2] == 1


@pytest.mark.sqlite_integration
def test_alert_seed_pending_within_window_reads_zero(factory) -> None:  # type: ignore[no-untyped-def]
    # created_at backdated only 5 min: still inside W, not yet overdue.
    _job, finding_id = seed_alert_job(
        factory, state=NotificationState.PENDING.value, age_minutes=5
    )
    series = _series(factory, metrics._now())
    assert len(series) == 1 and series[0][0] == finding_id and series[0][2] == 0


@pytest.mark.sqlite_integration
def test_alert_seed_sent_reads_zero(factory) -> None:  # type: ignore[no-untyped-def]
    _job, finding_id = seed_alert_job(factory, state=NotificationState.SENT.value)
    series = _series(factory, metrics._now())
    assert len(series) == 1 and series[0][0] == finding_id and series[0][2] == 0


@pytest.mark.sqlite_integration
def test_alert_seed_held_ownerless_never_emits(factory) -> None:  # type: ignore[no-untyped-def]
    # A-HELD (A39): a held job sets no finding series at all.
    seed_alert_job(factory, state=NotificationState.HELD_OWNERLESS.value)
    assert _series(factory, dt.datetime(2026, 6, 1, tzinfo=dt.UTC)) == []


@pytest.mark.sqlite_integration
def test_alert_seed_recorded_tier_wins_over_rescore(factory) -> None:  # type: ignore[no-untyped-def]
    # A-TIER: the job is recorded P1; the finding is re-scored to P3 later; the
    # series still shows the job's recorded tier, not the finding's current one.
    _job, finding_id = seed_alert_job(
        factory, state=NotificationState.FAILED.value, job_tier=Tier.P1.value,
    )
    rescore_finding(factory, finding_id=finding_id, tier=Tier.P3.value)
    series = _series(factory, metrics._now())
    assert len(series) == 1
    fid, tier, value = series[0]
    assert fid == finding_id and value == 1
    assert tier == Tier.P1.value, "recorded NotificationJob.tier must win over the re-score"


@pytest.mark.sqlite_integration
def test_alert_set_drives_job_to_sent_resolves(factory) -> None:  # type: ignore[no-untyped-def]
    # A-RESOLVE: a failed (firing) job driven to sent reads 0 (the alert resolves).
    _job, finding_id = seed_alert_job(factory, state=NotificationState.FAILED.value)
    assert _series(factory, metrics._now())[0][2] == 1
    updated = set_alert_job(factory, finding_id=finding_id, state=NotificationState.SENT.value)
    assert updated == 1
    assert _series(factory, metrics._now())[0][2] == 0


@pytest.mark.sqlite_integration
def test_alert_clear_removes_seeded_rows(factory) -> None:  # type: ignore[no-untyped-def]
    seed_alert_job(factory, state=NotificationState.FAILED.value, label="a")
    seed_alert_job(factory, state=NotificationState.SENT.value, label="b")
    assert len(_series(factory, metrics._now())) == 2
    removed = clear_alert_seed(factory)
    assert removed == 2
    assert _series(factory, metrics._now()) == []
    with factory() as session:
        assert session.query(NotificationJob).count() == 0


@pytest.mark.unit
def test_seed_alert_job_rejects_bad_state(factory) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(AlertSeedError):
        seed_alert_job(factory, state="not a state")


@pytest.mark.unit
def test_alert_seed_parser_rejects_unknown_state() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["alert-seed", "--state", "bogus"])
