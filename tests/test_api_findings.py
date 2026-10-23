"""Findings/assets resource API with the session guard (issue #82): I-RISK and reads."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from auth_helpers import CSRF, PASSWORD, login_cookie, make_user
from github_stub import FixtureTransport
from osv_stub import OsvFixtureTransport
from signals_stub import EpssFixtureTransport, KevFixtureTransport
from vulntriage.api.security import COOKIE_NAME
from vulntriage.db.enums import ScanTrigger
from vulntriage.db.models import Asset, AuditEntry, Base, Finding
from vulntriage.ingest.github import GitHubReader
from vulntriage.ingest.osv import OsvClient
from vulntriage.ingest.scan import enqueue_scan, run_pending_scans
from vulntriage.ingest.signals import EpssClient, KevClient
from vulntriage.main import create_app



pytestmark = pytest.mark.sqlite_integration  # task 13: the SQLite I-* integration layer

@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


def _seed_scan(factory: sessionmaker[Session], *, owner_email: str | None, criticality: str = "low",
               internet_facing: bool = False) -> int:
    """Register the pygoat fixture asset and run a full scan, creating findings."""
    with factory() as session:
        asset = Asset(name="pygoat", owner_name=None, owner_email=owner_email,
                      criticality=criticality, internet_facing=internet_facing,
                      repository_url="https://github.com/adeyosemanputra/pygoat")
        session.add(asset)
        session.flush()
        enqueue_scan(session, asset, ScanTrigger.REGISTRATION)
        aid = asset.id
        session.commit()
    run_pending_scans(
        factory,
        GitHubReader(FixtureTransport().client(), token_provider=lambda: None),
        OsvClient(OsvFixtureTransport().client()),
        KevClient(KevFixtureTransport().client()),
        EpssClient(EpssFixtureTransport().client()),
    )
    return aid


def _client(factory: sessionmaker[Session], *, username: str, role: str, email: str) -> TestClient:
    make_user(factory, username=username, role=role, email=email)
    client = TestClient(create_app(factory, reader=None, run_worker=False))
    client.cookies.set(COOKIE_NAME, login_cookie(client, username)[COOKIE_NAME])
    client.headers.update(CSRF)
    return client


def _finding_id(factory: sessionmaker[Session], package: str) -> str:
    with factory() as session:
        return str(session.scalar(select(Finding).where(Finding.package == package)).id)


# -- reads ------------------------------------------------------------------


def test_list_findings_requires_a_session(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_scan(factory, owner_email=None)
    anon = TestClient(create_app(factory, reader=None, run_worker=False))
    assert anon.get("/findings").status_code == 401


def test_list_findings_returns_findings_with_asset_in_rank_order(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_scan(factory, owner_email="o@example.com")
    client = _client(factory, username="lead", role="security lead", email="lead@example.com")
    response = client.get("/findings")
    assert response.status_code == 200
    body = response.json()
    packages = {f["package"] for f in body}
    assert packages == {"urllib3", "pyyaml"}
    first = body[0]
    # Shape: aliases, KEV/EPSS, rankReason, auditTrail and the joined asset.
    assert set(first) >= {"id", "vulnerabilityId", "aliases", "cveId", "tier", "kev", "epss",
                          "rankReason", "auditTrail", "asset", "briefStatus", "brief"}
    assert first["asset"]["repositoryUrl"].endswith("/pygoat")
    assert first["briefStatus"] == "pending" and first["brief"] is None
    urllib = next(f for f in body if f["package"] == "urllib3")
    assert "CVE-2023-43804" in urllib["aliases"] and urllib["kev"] == "KEV: listed"
    assert urllib["fixedVersion"] == "1.26.17"


def test_get_finding_404_for_unknown_id(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_scan(factory, owner_email=None)
    client = _client(factory, username="lead", role="security lead", email="lead@example.com")
    assert client.get("/findings/999999").status_code == 404
    fid = _finding_id(factory, "urllib3")
    assert client.get(f"/findings/{fid}").status_code == 200


# -- I-RISK: risk acceptance ------------------------------------------------


def test_security_lead_accepts_risk_with_a_reason(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_scan(factory, owner_email="owner@example.com")
    client = _client(factory, username="lead", role="security lead", email="lead@example.com")
    fid = _finding_id(factory, "urllib3")
    response = client.post(f"/findings/{fid}/risk-acceptance", json={"reason": "accepted for the pilot"})
    assert response.status_code == 200
    assert response.json()["status"] == "risk accepted"
    with factory() as session:
        entry = session.scalars(
            select(AuditEntry).where(AuditEntry.finding_id == int(fid)).order_by(AuditEntry.id.desc())
        ).first()
        assert entry.new_value == "risk accepted" and entry.previous_value == "open"
        assert entry.reason == "accepted for the pilot" and entry.actor != "re-scan"


@pytest.mark.parametrize("reason", ["", "   ", "\t\n"])
def test_empty_or_whitespace_reason_is_422_and_changes_nothing(factory, reason) -> None:  # type: ignore[no-untyped-def]
    _seed_scan(factory, owner_email=None)
    client = _client(factory, username="lead", role="security lead", email="lead@example.com")
    fid = _finding_id(factory, "urllib3")
    response = client.post(f"/findings/{fid}/risk-acceptance", json={"reason": reason})
    assert response.status_code == 422
    with factory() as session:
        assert session.get(Finding, int(fid)).status == "open"


def test_extra_fields_in_body_are_422(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_scan(factory, owner_email=None)
    client = _client(factory, username="lead", role="security lead", email="lead@example.com")
    fid = _finding_id(factory, "urllib3")
    for body in ({"reason": "ok", "status": "open"}, {"reason": "ok", "who": "me"}, {}):
        assert client.post(f"/findings/{fid}/risk-acceptance", json=body).status_code == 422


def test_owner_mismatch_is_403_and_changes_nothing(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_scan(factory, owner_email="someone@example.com")
    client = _client(factory, username="owner", role="asset owner", email="other@example.com")
    fid = _finding_id(factory, "urllib3")
    response = client.post(f"/findings/{fid}/risk-acceptance", json={"reason": "mine"})
    assert response.status_code == 403
    with factory() as session:
        assert session.get(Finding, int(fid)).status == "open"


def test_matching_owner_may_accept(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_scan(factory, owner_email="Owner@Example.com")  # trim + case-fold match
    client = _client(factory, username="owner", role="asset owner", email=" owner@example.com ")
    fid = _finding_id(factory, "urllib3")
    assert client.post(f"/findings/{fid}/risk-acceptance", json={"reason": "owned"}).status_code == 200


def test_error_order_404_before_owner_before_422(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_scan(factory, owner_email="someone@example.com")
    owner = _client(factory, username="owner", role="asset owner", email="other@example.com")
    # Unknown finding with an empty reason -> 404 (not 422).
    assert owner.post("/findings/999999/risk-acceptance", json={"reason": ""}).status_code == 404
    # Owner mismatch with an empty reason -> 403 (not 422).
    fid = _finding_id(factory, "urllib3")
    assert owner.post(f"/findings/{fid}/risk-acceptance", json={"reason": ""}).status_code == 403


def test_accept_on_non_open_finding_is_409(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_scan(factory, owner_email=None)
    client = _client(factory, username="lead", role="security lead", email="lead@example.com")
    fid = _finding_id(factory, "urllib3")
    assert client.post(f"/findings/{fid}/risk-acceptance", json={"reason": "once"}).status_code == 200
    # A second acceptance (now risk accepted, not open) -> 409.
    assert client.post(f"/findings/{fid}/risk-acceptance", json={"reason": "again"}).status_code == 409


def test_missing_csrf_header_is_403(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_scan(factory, owner_email=None)
    make_user(factory, username="lead", role="security lead", email="lead@example.com")
    client = TestClient(create_app(factory, reader=None, run_worker=False))
    client.cookies.set(COOKIE_NAME, login_cookie(client, "lead")[COOKIE_NAME])  # no CSRF header
    fid = _finding_id(factory, "urllib3")
    response = client.post(f"/findings/{fid}/risk-acceptance", json={"reason": "x"})
    assert response.status_code == 403
    with factory() as session:
        assert session.get(Finding, int(fid)).status == "open"


# -- assets: list, get, update, rescan --------------------------------------


def test_list_and_get_asset(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _seed_scan(factory, owner_email="o@example.com", criticality="high")
    client = _client(factory, username="lead", role="security lead", email="lead@example.com")
    listing = client.get("/assets")
    assert listing.status_code == 200
    row = listing.json()[0]
    assert set(row) >= {"ownerName", "ownerEmail", "criticality", "internetFacing", "scanStatus"}
    assert client.get(f"/assets/{aid}").json()["criticality"] == "high"
    assert client.get("/assets/999999").status_code == 404


def test_patch_asset_requires_security_lead_and_audits_changes(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _seed_scan(factory, owner_email=None, criticality="low")
    owner = _client(factory, username="owner", role="asset owner", email="o@example.com")
    assert owner.patch(f"/assets/{aid}", json={"criticality": "high"}).status_code == 403

    lead = _client(factory, username="lead", role="security lead", email="lead@example.com")
    response = lead.patch(f"/assets/{aid}", json={"criticality": "critical",
                                                  "ownerEmail": "new@example.com"})
    assert response.status_code == 200
    assert response.json()["criticality"] == "critical"
    assert response.json()["ownerEmail"] == "new@example.com"
    with factory() as session:
        entries = list(session.scalars(select(AuditEntry).where(AuditEntry.asset_id == aid)))
        fields = {e.field for e in entries}
    assert fields == {"criticality", "ownerEmail"}


def test_patch_empty_body_and_extra_field_are_422(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _seed_scan(factory, owner_email=None)
    lead = _client(factory, username="lead", role="security lead", email="lead@example.com")
    assert lead.patch(f"/assets/{aid}", json={}).status_code == 422
    assert lead.patch(f"/assets/{aid}", json={"name": "nope"}).status_code == 422
    assert lead.patch(f"/assets/{aid}", json={"criticality": "urgent"}).status_code == 422


def test_patch_unknown_asset_is_404_before_role_check(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_scan(factory, owner_email=None)
    owner = _client(factory, username="owner", role="asset owner", email="o@example.com")
    # 404 comes before the role 403 per the contract order.
    assert owner.patch("/assets/999999", json={"criticality": "high"}).status_code == 404


def test_rescan_returns_202_and_enqueues(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _seed_scan(factory, owner_email="o@example.com")
    lead = _client(factory, username="lead", role="security lead", email="lead@example.com")
    assert lead.post(f"/assets/{aid}/rescan").status_code == 202
    assert lead.post("/assets/999999/rescan").status_code == 404


def test_rescan_owner_mismatch_is_403(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _seed_scan(factory, owner_email="someone@example.com")
    owner = _client(factory, username="owner", role="asset owner", email="other@example.com")
    assert owner.post(f"/assets/{aid}/rescan").status_code == 403
    matching = _client(factory, username="o2", role="asset owner", email="someone@example.com")
    assert matching.post(f"/assets/{aid}/rescan").status_code == 202
