"""Service API: n8n/responder allowlists, top-tier jobs and idempotency (issue #83).

Covers the submission scope of task 10a: the n8n and responder bearer
allowlists (I-AUTH-N8N's submission subset and I-RESP-*), top-tier
NotificationJob creation with the lifecycle idempotency key, and I-OWNER-ONCE's
job half (a second refresh creates no second job). The n8n claim/report/digest
behaviour is Showcase; here those endpoints are contract-only stubs.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from auth_helpers import CSRF, login_cookie, make_user
from github_stub import FixtureTransport
from osv_stub import OsvFixtureTransport
from signals_stub import EpssFixtureTransport, KevFixtureTransport
from vulntriage.api.security import COOKIE_NAME
from vulntriage.db.enums import ScanTrigger
from vulntriage.db.models import Asset, Base, Finding, Lifecycle, NotificationJob
from vulntriage.ingest.github import GitHubReader
from vulntriage.ingest.osv import OsvClient
from vulntriage.ingest.scan import enqueue_scan, run_pending_scans
from vulntriage.ingest.signals import EpssClient, KevClient
from vulntriage.main import create_app


pytestmark = pytest.mark.sqlite_integration  # task 13: the SQLite I-* integration layer

N8N = "n8n-secret-token"
MCP = "mcp-secret-token"
RESP = "responder-secret-token"


@pytest.fixture()
def tokens(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("N8N_API_TOKEN", N8N)
    monkeypatch.setenv("MCP_API_TOKEN", MCP)
    monkeypatch.setenv("RESPONDER_API_TOKEN", RESP)


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


def _seed_p1_scan(factory: sessionmaker[Session]) -> int:
    """Register an exposed pygoat asset and scan, so urllib3 (KEV-listed) is P1."""
    with factory() as session:
        asset = Asset(name="pygoat", owner_name=None, owner_email="o@example.com",
                      criticality="high", internet_facing=True,
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


def _client(factory: sessionmaker[Session]) -> TestClient:
    return TestClient(create_app(factory, reader=None, run_worker=False))


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# -- n8n allowlist (I-AUTH-N8N submission subset) ---------------------------


def test_signals_refresh_and_scans_need_the_n8n_token(factory, tokens) -> None:  # type: ignore[no-untyped-def]
    client = _client(factory)
    for path in ("/signals/refresh", "/scans"):
        assert client.post(path).status_code == 401  # no credential
        assert client.post(path, headers=_bearer("wrong")).status_code == 401  # invalid
        assert client.post(path, headers=_bearer(MCP)).status_code == 403  # wrong consumer
        assert client.post(path, headers=_bearer(N8N)).status_code == 202  # allowed


def test_session_cookie_on_an_n8n_operation_is_403(factory, tokens) -> None:  # type: ignore[no-untyped-def]
    make_user(factory, username="lead", role="security lead", email="l@example.com")
    client = _client(factory)
    client.cookies.set(COOKIE_NAME, login_cookie(client, "lead")[COOKIE_NAME])
    client.headers.update(CSRF)
    assert client.post("/signals/refresh").status_code == 403


def test_n8n_token_cannot_touch_frontend_write_operations(factory, tokens) -> None:  # type: ignore[no-untyped-def]
    aid = _seed_p1_scan(factory)
    client = _client(factory)
    # A service token on a cookie operation is 403 (no risk acceptance, no edit).
    fid = _finding_id(factory, "urllib3")
    assert client.post(f"/findings/{fid}/risk-acceptance", json={"reason": "x"},
                       headers=_bearer(N8N)).status_code == 403
    assert client.patch(f"/assets/{aid}", json={"criticality": "low"},
                        headers=_bearer(N8N)).status_code == 403
    with factory() as session:
        assert session.get(Finding, int(fid)).status == "open"


def test_notification_jobs_stub_enforces_the_allowlist_and_kind(factory, tokens) -> None:  # type: ignore[no-untyped-def]
    client = _client(factory)
    assert client.get("/notification-jobs").status_code == 401
    assert client.get("/notification-jobs", headers=_bearer(RESP)).status_code == 403
    assert client.get("/notification-jobs", headers=_bearer(N8N)).json() == []
    assert client.get("/notification-jobs?kind=bogus", headers=_bearer(N8N)).status_code == 422
    assert client.get("/notification-jobs?kind=top tier", headers=_bearer(N8N)).status_code == 200


def test_weekly_digest_stub_validates_week(factory, tokens) -> None:  # type: ignore[no-untyped-def]
    client = _client(factory)
    assert client.get("/reports/weekly-digest", headers=_bearer(N8N)).status_code == 200
    assert client.get("/reports/weekly-digest?week=2026-W43", headers=_bearer(N8N)).status_code == 200
    assert client.get("/reports/weekly-digest?week=nope", headers=_bearer(N8N)).status_code == 422
    body = client.get("/reports/weekly-digest?week=2026-W43", headers=_bearer(N8N)).json()
    assert body["week"] == "2026-W43" and body["findings"] == []


# -- top-tier job creation and idempotency (I-OWNER-ONCE, job half) ---------


def test_scan_creates_one_top_tier_job_for_a_p1_finding(factory, tokens) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_scan(factory)
    with factory() as session:
        urllib = session.scalar(select(Finding).where(Finding.package == "urllib3"))
        assert urllib.tier == "P1"  # KEV-listed + exposed
        jobs = list(session.scalars(select(NotificationJob)))
    assert len(jobs) == 1
    assert jobs[0].kind == "top tier" and jobs[0].state == "pending"
    assert jobs[0].tier == "P1"
    # The traceparent is a valid, non-zero W3C value set at creation.
    tp = jobs[0].traceparent
    assert tp.startswith("00-") and len(tp.split("-")) == 4
    assert int(tp.split("-")[1], 16) != 0 and int(tp.split("-")[2], 16) != 0


def test_a_second_refresh_creates_no_second_job(factory, tokens) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_scan(factory)
    client = _client(factory)
    assert client.post("/signals/refresh", headers=_bearer(N8N)).status_code == 202
    assert client.post("/signals/refresh", headers=_bearer(N8N)).status_code == 202
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(NotificationJob)) == 1


def test_lifecycle_records_the_p1_entry_and_due_date(factory, tokens) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_scan(factory)
    with factory() as session:
        urllib = session.scalar(select(Finding).where(Finding.package == "urllib3"))
        lifecycle = session.get(Lifecycle, urllib.current_lifecycle_id)
        assert lifecycle.entered_p1_at is not None
        # P1 window is 7 days from the lifecycle start (A27).
        delta = lifecycle.due_at - lifecycle.started_at
        assert abs(delta.total_seconds() - 7 * 24 * 3600) < 2


def test_non_p1_finding_gets_no_job(factory) -> None:  # type: ignore[no-untyped-def]
    # pygoat on a non-exposed, low asset: urllib3 is KEV-listed but not exposed
    # -> P2, pyyaml -> P3; neither is top tier, so no job.
    with factory() as session:
        asset = Asset(name="pygoat", owner_name=None, owner_email=None, criticality="low",
                      internet_facing=False, repository_url="https://github.com/adeyosemanputra/pygoat")
        session.add(asset)
        session.flush()
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
        assert session.scalar(select(func.count()).select_from(NotificationJob)) == 0


# -- responder read operations (I-RESP-*) -----------------------------------


def test_responder_get_finding_allowlist(factory, tokens) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_scan(factory)
    fid = _finding_id(factory, "urllib3")
    client = _client(factory)
    assert client.get(f"/responder/findings/{fid}").status_code == 401  # no credential
    assert client.get(f"/responder/findings/{fid}", headers=_bearer(N8N)).status_code == 403
    assert client.get(f"/responder/findings/{fid}", headers=_bearer(MCP)).status_code == 403
    ok = client.get(f"/responder/findings/{fid}", headers=_bearer(RESP))
    assert ok.status_code == 200 and ok.json()["package"] == "urllib3"
    assert client.get("/responder/findings/999999", headers=_bearer(RESP)).status_code == 404


def test_responder_list_jobs_allowlist_and_filter(factory, tokens) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_scan(factory)
    fid = _finding_id(factory, "urllib3")
    client = _client(factory)
    # Missing findingId -> 422; bad state -> 422; unknown findingId -> 200 [].
    assert client.get("/responder/notification-jobs", headers=_bearer(RESP)).status_code == 422
    assert client.get("/responder/notification-jobs?findingId=1&state=weird",
                      headers=_bearer(RESP)).status_code == 422
    assert client.get("/responder/notification-jobs?findingId=999999",
                      headers=_bearer(RESP)).json() == []
    # The P1 finding has one top-tier job; the responder sees it with no recipient.
    jobs = client.get(f"/responder/notification-jobs?findingId={fid}", headers=_bearer(RESP)).json()
    assert len(jobs) == 1
    assert set(jobs[0]) == {"id", "kind", "state", "createdAt", "findingId",
                            "traceparent", "attempts", "lastErrorCode"}
    assert "recipient" not in jobs[0] and "advisorySummary" not in jobs[0]
    # A session cookie or n8n token is refused.
    assert client.get(f"/responder/notification-jobs?findingId={fid}",
                      headers=_bearer(N8N)).status_code == 403


def test_no_service_token_configured_refuses_everything(factory) -> None:  # type: ignore[no-untyped-def]
    # With no env tokens set, a presented token is "unknown" -> 401; a cookie 403.
    client = _client(factory)
    assert client.post("/signals/refresh", headers=_bearer("anything")).status_code == 401


def _finding_id(factory: sessionmaker[Session], package: str) -> str:
    with factory() as session:
        return str(session.scalar(select(Finding).where(Finding.package == package)).id)
