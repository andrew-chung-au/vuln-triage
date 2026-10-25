"""Operator commands (task 9's user-creation half; defect #176).

There is no sign-up: a dashboard user is created only by an operator running this
command, which the dev, prod and local-demo environments need to have anyone
sign in. Task 9's wording: it "creates a dashboard user (username, display name,
email, role and a password read from a prompt, never from the command line)",
and its check is "a user created by the command signing in while the stored
password value is an Argon2id hash and not the password".

Usage:
    python -m vulntriage.manage create-user --username U --display-name "D" \\
        --email e@x --role "security lead"

The password is NEVER a command-line argument. It is read from an interactive
prompt when a terminal is attached (``getpass``), or from stdin when one is not
(so Compose/CI can pipe it: ``docker compose run -T backend python -m
vulntriage.manage create-user ... < password-file``). The stored value is an
Argon2id hash (``api.security.hash_password``), never the plaintext.

----

The ``alert-*`` subcommands are the **firing-state seam** for the ``alert``
Compose job (task 27, #159). They put a ``top tier`` ``NotificationJob`` into a
named state (``failed`` / ``pending``-backdated / ``sent`` / ``held: *``) with a
set ``created_at`` / ``sent_at`` / ``tier``, committed to the **same Postgres the
overdue gauge reads** (``DATABASE_URL`` in the container environment). The alert
then fires from **stored job state** through the task-26 Grafana rule, not from
an in-test simulation (the #172 Compose-path sweep's requirement, recorded on
#159). They are test/harness commands run in-container by ``ci/test-compose.sh``
(``docker compose run -T --rm backend python -m vulntriage.manage alert-seed
...``); they never run in production and never change the backend's W
(``_OVERDUE_WINDOW`` stays 30 min, A33) — only the stored row's timestamps.
"""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import sys
from collections.abc import Callable
from typing import TextIO

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.api.security import hash_password
from vulntriage.db.enums import (
    Ecosystem,
    FindingStatus,
    NotificationKind,
    NotificationRecipient,
    NotificationState,
    Tier,
    UserRole,
)
from vulntriage.db.models import (
    Asset,
    Finding,
    Lifecycle,
    NotificationJob,
    User,
    Vulnerability,
)
from vulntriage.db.session import create_db_engine, create_session_factory

_ROLE_VALUES = tuple(r.value for r in UserRole)
_STATE_VALUES = tuple(s.value for s in NotificationState)
_TIER_VALUES = tuple(t.value for t in Tier)


class UserCreationError(RuntimeError):
    """A create-user command could not complete (bad role, duplicate, empty password)."""


class AlertSeedError(RuntimeError):
    """An alert-* seam command could not complete (bad reference, bad state)."""


def read_password(
    *,
    stdin: TextIO | None = None,
    isatty: Callable[[], bool] | None = None,
    getpass_fn: Callable[[str], str] = getpass.getpass,
) -> str:
    """Read the password from a prompt (tty) or from stdin (piped).

    Never from the command line. When a terminal is attached, prompt with
    ``getpass`` (no echo). When not (Compose/CI piping input), read one line from
    stdin and strip the trailing newline. The seams (``stdin``/``isatty``/
    ``getpass_fn``) are injectable so both paths are unit-testable without a tty.

    VERIFY: ``getpass.getpass`` with no terminal may fall back to stdin with a
    warning on some platforms; the explicit isatty branch avoids relying on that.
    """
    stream = stdin if stdin is not None else sys.stdin
    at_tty = isatty() if isatty is not None else stream.isatty()
    if at_tty:
        password = getpass_fn("Password: ")
    else:
        line = stream.readline()
        if line == "":
            raise UserCreationError("no password on stdin (and no terminal to prompt)")
        password = line.rstrip("\n")
    if not password:
        raise UserCreationError("password must not be empty")
    return password


def create_user(
    factory: sessionmaker[Session],
    *,
    username: str,
    display_name: str,
    email: str,
    role: str,
    password: str,
) -> int:
    """Insert one dashboard user with an Argon2id password hash; return its id.

    Validates the role against :class:`UserRole` and rejects a duplicate
    username (the unique constraint) with a clear error. The password is hashed
    with :func:`vulntriage.api.security.hash_password` (Argon2id); the plaintext
    is never stored or logged.
    """
    if role not in _ROLE_VALUES:
        raise UserCreationError(f"role must be one of {_ROLE_VALUES}; got {role!r}")
    user = User(
        username=username,
        display_name=display_name,
        email=email,
        role=role,
        password_hash=hash_password(password),
    )
    try:
        with factory() as session:
            session.add(user)
            session.commit()
            return user.id
    except IntegrityError as exc:
        raise UserCreationError(f"could not create user {username!r} (duplicate username?)") from exc


def _cmd_create_user(args: argparse.Namespace) -> int:
    password = read_password()
    factory = create_session_factory(create_db_engine())
    user_id = create_user(
        factory,
        username=args.username,
        display_name=args.display_name,
        email=args.email,
        role=args.role,
        password=password,
    )
    print(f"created user {args.username!r} (id {user_id}, role {args.role!r})")
    return 0


# ---------------------------------------------------------------------------
# Firing-state seam for the `alert` Compose job (task 27, #159)
# ---------------------------------------------------------------------------
#
# These build a self-contained finding -> lifecycle -> top-tier job chain
# directly in stored state, so `compute_overdue_series` (the overdue gauge's
# callback) reads them exactly as it reads a job produced by a real scan:
# resolved to a finding id through the job's lifecycle, with the stored
# `state` / `created_at` / `sent_at` / `tier`. The seed is deterministic (it
# does not depend on a live feed or the pygoat P1 fixture), which is what the
# A-* cases need to drive each named state on demand. A journey-driven real P1
# job (as the telemetry harness registers) is an equally valid source; the seam
# to SET the stored state and backdate `created_at` is required either way, and
# that is all these commands do — they never touch the backend's W.

_SEED_MARKER = "vt-alert-seed"


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _seed_asset(session: Session, label: str) -> Asset:
    """Create (or reuse) the alert-seam asset the seeded findings hang off.

    One shared asset per label keeps the seeded rows easy to find and clear.
    Its owner email is set, so an ownerless *job* in A-HELD comes from the job's
    stored state, not from a missing owner on the asset.
    """
    name = f"{_SEED_MARKER}:{label}"
    asset = session.scalar(select(Asset).where(Asset.name == name))
    if asset is not None:
        return asset
    asset = Asset(
        name=name,
        owner_name="Alert Seam Owner",
        owner_email="seam-owner@alert.test",
        criticality="high",
        internet_facing=True,
        repository_url="https://example.test/alert-seam",
    )
    session.add(asset)
    session.flush()
    return asset


def _seed_finding(session: Session, asset: Asset, tier: str) -> Finding:
    """Create a finding + its current lifecycle for ``asset`` at ``tier``.

    The finding is ``open`` so it is in scope for the overdue series; its current
    lifecycle is the row ``compute_overdue_series`` joins the job back to for the
    ``finding_id`` label. A throwaway vulnerability row satisfies the finding's
    non-null FK without a CVE (the alert payload carries finding id + tier only).
    """
    vuln = Vulnerability(identity_key=f"{_SEED_MARKER}-{_utcnow().timestamp()}", cve_id=None)
    session.add(vuln)
    session.flush()
    now = _utcnow()
    finding = Finding(
        asset_id=asset.id,
        vulnerability_id=vuln.id,
        ecosystem=Ecosystem.PYPI.value,
        package=f"{_SEED_MARKER}-pkg",
        fixed_version=None,
        status=FindingStatus.OPEN.value,
        tier=tier,
        rank_inputs={},
        rank_reason=f"{_SEED_MARKER}: deterministic alert-seam finding",
        first_detected_at=now,
    )
    session.add(finding)
    session.flush()
    lifecycle = Lifecycle(
        finding_id=finding.id,
        number=1,
        started_at=now,
        due_at=now + dt.timedelta(days=7),
        highest_tier=tier,
        entered_p1_at=now if tier == Tier.P1.value else None,
    )
    session.add(lifecycle)
    session.flush()
    finding.current_lifecycle_id = lifecycle.id
    session.flush()
    return finding


def _backdated_created_at(now: dt.datetime, age_minutes: int | None) -> dt.datetime:
    return now - dt.timedelta(minutes=age_minutes if age_minutes is not None else 0)


def seed_alert_job(
    factory: sessionmaker[Session],
    *,
    state: str,
    job_tier: str = Tier.P1.value,
    finding_tier: str | None = None,
    age_minutes: int | None = None,
    sent_age_hours: float | None = None,
    label: str | None = None,
    now: Callable[[], dt.datetime] = _utcnow,
) -> tuple[int, int]:
    """Create one ``top tier`` job in ``state`` from stored state; return (job_id, finding_id).

    - ``job_tier`` is the ``NotificationJob.tier`` recorded at creation (A-TIER:
      this, not the finding's current tier, is what the series and alert show).
    - ``finding_tier`` is the finding's current tier (defaults to ``job_tier``);
      pass a different value to set up the A-TIER "recorded tier wins over a
      later re-score" check in one step.
    - ``age_minutes`` backdates ``created_at`` to ``now - age_minutes`` (A33: for
      a ``pending``/``claimed`` job, > 30 puts it past W without waiting; the
      backend's ``_OVERDUE_WINDOW`` is unchanged).
    - ``sent_age_hours`` backdates ``sent_at`` for a ``sent`` job (> 24 drops the
      series; the core A-RESOLVE only needs ``sent`` -> 0 + resolve).
    """
    if state not in _STATE_VALUES:
        raise AlertSeedError(f"state must be one of {_STATE_VALUES}; got {state!r}")
    if job_tier not in _TIER_VALUES:
        raise AlertSeedError(f"tier must be one of {_TIER_VALUES}; got {job_tier!r}")
    f_tier = finding_tier if finding_tier is not None else job_tier
    if f_tier not in _TIER_VALUES:
        raise AlertSeedError(f"finding-tier must be one of {_TIER_VALUES}; got {f_tier!r}")

    seed_label = label or state.replace(":", "-").replace(" ", "-")
    created = _backdated_created_at(now(), age_minutes)
    sent_at = None
    if sent_age_hours is not None:
        sent_at = now() - dt.timedelta(hours=sent_age_hours)
    elif state == NotificationState.SENT.value:
        sent_at = now()

    with factory() as session:
        asset = _seed_asset(session, seed_label)
        finding = _seed_finding(session, asset, f_tier)
        job = NotificationJob(
            lifecycle_id=finding.current_lifecycle_id,
            kind=NotificationKind.TOP_TIER.value,
            recipient=NotificationRecipient.OWNER.value,
            idempotency_key=f"{_SEED_MARKER}:{finding.current_lifecycle_id}:{now().timestamp()}",
            state=state,
            traceparent="00-" + "0" * 32 + "-" + "0" * 16 + "-01",  # valid-shaped, never read by the gauge
            tier=job_tier,
            created_at=created,
            sent_at=sent_at,
        )
        session.add(job)
        session.commit()
        return job.id, finding.id


def set_alert_job(
    factory: sessionmaker[Session],
    *,
    finding_id: int,
    state: str,
    age_minutes: int | None = None,
    sent_age_hours: float | None = None,
    now: Callable[[], dt.datetime] = _utcnow,
) -> int:
    """Flip every top-tier job for ``finding_id`` to ``state`` (drive A-RESOLVE).

    Returns how many jobs were updated. Used to drive a fired job to ``sent``
    (the series goes to 0 and the alert resolves) without touching the recorded
    tier. A missing ``sent_at`` for a ``sent`` job is set to ``now``.
    """
    if state not in _STATE_VALUES:
        raise AlertSeedError(f"state must be one of {_STATE_VALUES}; got {state!r}")
    updated = 0
    with factory() as session:
        lifecycle_ids = session.scalars(
            select(Lifecycle.id).where(Lifecycle.finding_id == finding_id)
        ).all()
        jobs = session.scalars(
            select(NotificationJob).where(
                NotificationJob.lifecycle_id.in_(lifecycle_ids),
                NotificationJob.kind == NotificationKind.TOP_TIER.value,
            )
        ).all()
        for job in jobs:
            job.state = state
            if age_minutes is not None:
                job.created_at = _backdated_created_at(now(), age_minutes)
            if state == NotificationState.SENT.value:
                job.sent_at = now() - dt.timedelta(hours=sent_age_hours or 0)
            updated += 1
        session.commit()
    return updated


def rescore_finding(
    factory: sessionmaker[Session],
    *,
    finding_id: int,
    tier: str,
) -> None:
    """Change a finding's current tier (A-TIER: a later re-score).

    The job's recorded ``NotificationJob.tier`` is deliberately NOT touched, so
    the series/alert still show the job's original tier while the finding's
    current tier differs — exactly the A-TIER invariant.
    """
    if tier not in _TIER_VALUES:
        raise AlertSeedError(f"tier must be one of {_TIER_VALUES}; got {tier!r}")
    with factory() as session:
        finding = session.get(Finding, finding_id)
        if finding is None:
            raise AlertSeedError(f"no finding with id {finding_id}")
        finding.tier = tier
        session.commit()


def clear_alert_seed(factory: sessionmaker[Session]) -> int:
    """Delete every row the alert seam created; return how many assets were removed.

    Keeps each A-* case independent (one firing job at a time), mirroring a
    fresh stack. Only rows whose asset name carries the seam marker are removed.
    """
    removed = 0
    with factory() as session:
        asset_ids = session.scalars(
            select(Asset.id).where(Asset.name.like(f"{_SEED_MARKER}:%"))
        ).all()
        if not asset_ids:
            return 0
        finding_ids = session.scalars(
            select(Finding.id).where(Finding.asset_id.in_(asset_ids))
        ).all()
        lifecycle_ids = session.scalars(
            select(Lifecycle.id).where(Lifecycle.finding_id.in_(finding_ids))
        ).all()
        if lifecycle_ids:
            session.execute(
                delete(NotificationJob).where(NotificationJob.lifecycle_id.in_(lifecycle_ids))
            )
        if finding_ids:
            session.execute(delete(Lifecycle).where(Lifecycle.finding_id.in_(finding_ids)))
            session.execute(delete(Finding).where(Finding.id.in_(finding_ids)))
        session.execute(delete(Asset).where(Asset.id.in_(asset_ids)))
        session.commit()
        removed = len(asset_ids)
    return removed


def _emit(data: dict) -> None:
    """Print one JSON line the alert harness parses from stdout (never a secret)."""
    print("VT_MANAGE_RESULT " + json.dumps(data, sort_keys=True))


def _cmd_alert_seed(args: argparse.Namespace) -> int:
    factory = create_session_factory(create_db_engine())
    job_id, finding_id = seed_alert_job(
        factory,
        state=args.state,
        job_tier=args.tier,
        finding_tier=args.finding_tier,
        age_minutes=args.age_minutes,
        sent_age_hours=args.sent_age_hours,
        label=args.label,
    )
    _emit({"cmd": "alert-seed", "job_id": job_id, "finding_id": finding_id, "state": args.state})
    return 0


def _cmd_alert_set(args: argparse.Namespace) -> int:
    factory = create_session_factory(create_db_engine())
    updated = set_alert_job(
        factory,
        finding_id=args.finding_id,
        state=args.state,
        age_minutes=args.age_minutes,
        sent_age_hours=args.sent_age_hours,
    )
    _emit({"cmd": "alert-set", "finding_id": args.finding_id, "state": args.state, "updated": updated})
    return 0


def _cmd_alert_rescore(args: argparse.Namespace) -> int:
    factory = create_session_factory(create_db_engine())
    rescore_finding(factory, finding_id=args.finding_id, tier=args.tier)
    _emit({"cmd": "alert-rescore", "finding_id": args.finding_id, "tier": args.tier})
    return 0


def _cmd_alert_clear(args: argparse.Namespace) -> int:
    factory = create_session_factory(create_db_engine())
    removed = clear_alert_seed(factory)
    _emit({"cmd": "alert-clear", "removed_assets": removed})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m vulntriage.manage")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-user", help="create a dashboard user (password read from a prompt/stdin)")
    create.add_argument("--username", required=True)
    create.add_argument("--display-name", required=True, dest="display_name")
    create.add_argument("--email", required=True)
    create.add_argument("--role", required=True, choices=_ROLE_VALUES)
    # Deliberately NO --password: the password is never a command-line argument.
    create.set_defaults(func=_cmd_create_user)

    # --- alert firing-state seam (task 27, #159; test/harness only) --------
    seed = sub.add_parser(
        "alert-seed",
        help="(#159 test seam) create a top-tier NotificationJob in a named state, backdated",
    )
    seed.add_argument("--state", required=True, choices=_STATE_VALUES)
    seed.add_argument(
        "--tier", default=Tier.P1.value, choices=_TIER_VALUES,
        help="the NotificationJob.tier recorded at creation (A-TIER)",
    )
    seed.add_argument(
        "--finding-tier", default=None, choices=_TIER_VALUES, dest="finding_tier",
        help="the finding's current tier (defaults to --tier); set it different to stage A-TIER",
    )
    seed.add_argument(
        "--age-minutes", type=int, default=None, dest="age_minutes",
        help="backdate created_at to now - AGE_MINUTES (> 30 is past W for pending/claimed)",
    )
    seed.add_argument(
        "--sent-age-hours", type=float, default=None, dest="sent_age_hours",
        help="backdate sent_at for a sent job (> 24 drops the series)",
    )
    seed.add_argument("--label", default=None, help="a label for the seeded asset (defaults to the state)")
    seed.set_defaults(func=_cmd_alert_seed)

    aset = sub.add_parser(
        "alert-set",
        help="(#159 test seam) flip a finding's top-tier job(s) to a named state (e.g. drive to sent)",
    )
    aset.add_argument("--finding-id", required=True, type=int, dest="finding_id")
    aset.add_argument("--state", required=True, choices=_STATE_VALUES)
    aset.add_argument("--age-minutes", type=int, default=None, dest="age_minutes")
    aset.add_argument("--sent-age-hours", type=float, default=None, dest="sent_age_hours")
    aset.set_defaults(func=_cmd_alert_set)

    rescore = sub.add_parser(
        "alert-rescore",
        help="(#159 test seam) change a finding's current tier (recorded job tier must win)",
    )
    rescore.add_argument("--finding-id", required=True, type=int, dest="finding_id")
    rescore.add_argument("--tier", required=True, choices=_TIER_VALUES)
    rescore.set_defaults(func=_cmd_alert_rescore)

    clear = sub.add_parser(
        "alert-clear", help="(#159 test seam) delete every row the alert seam created",
    )
    clear.set_defaults(func=_cmd_alert_clear)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (UserCreationError, AlertSeedError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
