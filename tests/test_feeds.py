"""Feed-client wiring and the VT_FEEDS fixture mode (task 40 / #172).

Covers the settings gate (pure, fail-closed) and the end-to-end wiring: a
`fixtures`-mode scan through the replay transport yields a KEV-listed P1 finding
and exactly one `top tier` job, and `create_app` refuses to start when
`VT_FEEDS=fixtures` outside dev/test. All under `make test` (SQLite, no Docker,
no network — the replay transport is in-process).
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.ingest.feeds import build_feed_clients, fixtures_root
from vulntriage.ingest.settings import FEEDS_FIXTURES
from vulntriage.ingest.scan import enqueue_scan, run_pending_scans
from vulntriage.ingest.settings import (
    FeedsConfigurationError,
    get_feeds_mode,
    is_non_production_environment,
    require_feeds_allowed,
)
from vulntriage.db.enums import NotificationKind, ScanTrigger
from vulntriage.db.models import Asset, Base, Finding, NotificationJob

# No module-level pytestmark: the settings/create_app cases are `unit`, the scan
# case is `sqlite_integration`; each is marked explicitly below so no case
# carries both markers.


# -- the settings gate (pure; a mapping is passed, nothing touches os.environ) --


@pytest.mark.unit
def test_get_feeds_mode_defaults_to_live_when_unset() -> None:
    assert get_feeds_mode({}) == "live"
    assert get_feeds_mode({"VT_FEEDS": ""}) == "live"


@pytest.mark.unit
def test_get_feeds_mode_accepts_live_and_fixtures() -> None:
    assert get_feeds_mode({"VT_FEEDS": "live"}) == "live"
    assert get_feeds_mode({"VT_FEEDS": "fixtures"}) == "fixtures"


@pytest.mark.unit
def test_get_feeds_mode_unknown_value_errors_no_silent_fallback() -> None:
    # A typo like "fixture" must stop start-up, not quietly run against live.
    with pytest.raises(FeedsConfigurationError):
        get_feeds_mode({"VT_FEEDS": "fixture"})
    with pytest.raises(FeedsConfigurationError):
        get_feeds_mode({"VT_FEEDS": "prod"})


@pytest.mark.unit
def test_non_production_environment_is_explicit_dev_or_test_only() -> None:
    assert is_non_production_environment({"DEPLOYMENT_ENVIRONMENT": "dev"}) is True
    assert is_non_production_environment({"DEPLOYMENT_ENVIRONMENT": "test"}) is True
    # Fail closed: unset, prod and unknown all count as production.
    assert is_non_production_environment({}) is False
    assert is_non_production_environment({"DEPLOYMENT_ENVIRONMENT": "prod"}) is False
    assert is_non_production_environment({"DEPLOYMENT_ENVIRONMENT": "staging"}) is False


@pytest.mark.unit
def test_require_feeds_allowed_permits_fixtures_in_dev_and_test() -> None:
    assert require_feeds_allowed({"VT_FEEDS": "fixtures", "DEPLOYMENT_ENVIRONMENT": "dev"}) == "fixtures"
    assert require_feeds_allowed({"VT_FEEDS": "fixtures", "DEPLOYMENT_ENVIRONMENT": "test"}) == "fixtures"
    # live is always allowed.
    assert require_feeds_allowed({}) == "live"
    assert require_feeds_allowed({"DEPLOYMENT_ENVIRONMENT": "prod"}) == "live"


@pytest.mark.unit
def test_require_feeds_allowed_refuses_fixtures_outside_dev_test() -> None:
    # The unset case is the important one (fail closed): fixtures + no env refuses.
    with pytest.raises(FeedsConfigurationError):
        require_feeds_allowed({"VT_FEEDS": "fixtures"})
    with pytest.raises(FeedsConfigurationError):
        require_feeds_allowed({"VT_FEEDS": "fixtures", "DEPLOYMENT_ENVIRONMENT": "prod"})
    with pytest.raises(FeedsConfigurationError):
        require_feeds_allowed({"VT_FEEDS": "fixtures", "DEPLOYMENT_ENVIRONMENT": "staging"})


# -- end-to-end: a fixtures-mode scan yields a P1 finding + one top-tier job ----


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


@pytest.mark.sqlite_integration
def test_fixtures_mode_scan_produces_p1_and_one_top_tier_job(factory) -> None:  # type: ignore[no-untyped-def]
    """build_feed_clients('fixtures') drives a real scan to a KEV-listed P1 job.

    This proves the wiring that #172 adds: the OSV/KEV/EPSS/GitHub clients from
    the factory, run through the real run_pending_scans path, produce findings,
    ranking and exactly one `top tier` NotificationJob — with no network (the
    replay transport serves the committed fixtures).
    """
    feeds = build_feed_clients(FEEDS_FIXTURES, fixtures_root())
    with factory() as session:
        asset = Asset(
            name="pygoat", owner_name="Owner", owner_email="owner@team.example",
            criticality="high", internet_facing=True,
            repository_url="https://github.com/adeyosemanputra/pygoat",
        )
        session.add(asset)
        session.flush()
        enqueue_scan(session, asset, ScanTrigger.REGISTRATION)
        session.commit()

    run_pending_scans(factory, feeds.reader, feeds.osv, feeds.kev, feeds.epss)

    with factory() as session:
        # At least one P1 finding was produced from the fixtures.
        p1 = session.scalar(select(func.count()).select_from(Finding).where(Finding.tier == "P1"))
        assert p1 and p1 >= 1, "fixtures-mode scan produced no P1 finding"
        # Exactly one top-tier notification job.
        jobs = session.scalars(
            select(NotificationJob).where(NotificationJob.kind == NotificationKind.TOP_TIER.value)
        ).all()
        assert len(jobs) == 1, f"expected one top-tier job, got {len(jobs)}"
        assert jobs[0].tier == "P1"


# -- create_app refuses fixtures outside dev/test ------------------------------


@pytest.mark.unit
def test_create_app_refuses_fixtures_in_production(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """create_app fails closed: VT_FEEDS=fixtures with no dev/test env refuses."""
    from vulntriage.main import create_app

    monkeypatch.setenv("VT_FEEDS", "fixtures")
    monkeypatch.delenv("DEPLOYMENT_ENVIRONMENT", raising=False)  # unset = production
    with pytest.raises(FeedsConfigurationError):
        create_app(run_worker=False)


@pytest.mark.unit
def test_create_app_allows_fixtures_in_dev(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """create_app starts in dev with fixtures (the config is valid)."""
    from vulntriage.main import create_app

    monkeypatch.setenv("VT_FEEDS", "fixtures")
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "dev")
    app = create_app(run_worker=False)
    assert app is not None
