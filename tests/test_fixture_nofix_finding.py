"""The project-authored no-fixed-version fixture (#233, P-DEMO-BE).

The committed OSV fixtures all carry a fixed version, so no recorded repository
produced the finding the US-15 demo defect needs (a top-tier finding with NO fixed
version). #233 adds one project-authored advisory (invented id GHSA-fixture-nofix-0001,
invented alias CVE-2099-0001, open-ended range) for flask 2.3.3, which the committed
`fixture-owner/pip-app` repository already pins, plus an invented KEV row. This case
proves the scan of that repository yields exactly that finding at P1 with no fixed
version, and that the pygoat scan the telemetry journey asserts on is unchanged.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from github_stub import FixtureTransport
from osv_stub import OsvFixtureTransport
from signals_stub import EpssFixtureTransport, KevFixtureTransport
from vulntriage.db.enums import ScanTrigger
from vulntriage.db.models import Asset, Base, Finding
from vulntriage.ingest.github import GitHubReader
from vulntriage.ingest.osv import OsvClient
from vulntriage.ingest.scan import enqueue_scan, run_pending_scans
from vulntriage.ingest.signals import EpssClient, KevClient

pytestmark = pytest.mark.sqlite_integration


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


def _scan(factory: sessionmaker[Session], url: str, *, exposed: bool) -> dict[str, Finding]:
    with factory() as session:
        asset = Asset(
            name="a", owner_name="Owner", owner_email="owner@team.example",
            criticality="high" if exposed else "low", internet_facing=exposed, repository_url=url,
        )
        session.add(asset)
        session.commit()
        asset_id = asset.id
        enqueue_scan(session, asset, ScanTrigger.REGISTRATION)
        session.commit()
    run_pending_scans(
        factory,
        GitHubReader(FixtureTransport().client(), token_provider=lambda: None),
        OsvClient(OsvFixtureTransport().client()),
        KevClient(KevFixtureTransport().client()),
        EpssClient(EpssFixtureTransport().client()),
    )
    with factory() as session:
        return {f.package: f for f in session.scalars(select(Finding).where(Finding.asset_id == asset_id))}


def test_pip_app_scan_yields_a_top_tier_finding_with_no_fixed_version(factory) -> None:  # type: ignore[no-untyped-def]
    findings = _scan(factory, "https://github.com/fixture-owner/pip-app", exposed=True)
    assert set(findings) == {"flask"}
    flask = findings["flask"]
    assert flask.fixed_version is None
    assert flask.tier == "P1"
    assert flask.rank_reason.startswith("P1: KEV listed and exposed asset")
    assert "no fixed version" in flask.rank_reason


def test_pygoat_scan_is_unchanged_by_the_new_fixture(factory) -> None:  # type: ignore[no-untyped-def]
    findings = _scan(factory, "https://github.com/adeyosemanputra/pygoat", exposed=True)
    assert set(findings) == {"urllib3", "pyyaml"}
    assert findings["urllib3"].fixed_version == "1.26.17"
    assert findings["urllib3"].tier == "P1"
