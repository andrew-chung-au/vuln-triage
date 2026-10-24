"""Service-token operations: n8n, responder and the showcase stubs (issue #83).

Submission scope (real behaviour):
- ``POST /signals/refresh`` — re-score every asset's findings and create
  ``top tier`` notification jobs (idempotent); ``202``.
- ``POST /scans`` — start a re-scan of every registered asset; ``202``.
- ``GET /responder/findings/{id}`` and ``GET /responder/notification-jobs`` —
  the US-15 responder's two read operations.

Showcase stubs (contract-only, documented statuses; behaviour is tasks 32-35):
- ``GET /notification-jobs``, ``POST /notification-jobs/{id}/claim``,
  ``POST /notification-jobs/{id}/report``, ``GET /reports/weekly-digest``,
  and the three ``/mcp/`` operations.

The stubs exist so the task-14 conformance test can compare every operation and
the allowlist is enforced now; they run no claim, report, digest or MCP logic.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.api.serializers import (
    UNTRUSTED_LABEL,
    finding_to_wire,
    ranked_finding_to_wire,
    untrusted_advisory_data,
)
from vulntriage.api.service_auth import require_mcp, require_n8n, require_responder
from vulntriage.db.enums import NotificationKind, ScanTrigger
from vulntriage.db.models import (
    Asset,
    Finding,
    Lifecycle,
    NotificationJob,
    Vulnerability,
    VulnerabilityAlias,
)
from vulntriage.ingest.ranking import ranked_findings
from vulntriage.ingest.refresh import refresh_all
from vulntriage.ingest.scan import enqueue_scan

router = APIRouter()

_WEEK_RE = re.compile(r"^[0-9]{4}-W(0[1-9]|[1-4][0-9]|5[0-3])$")
_JOB_KINDS = {k.value for k in NotificationKind}
_RESPONDER_STATES = {"pending", "claimed", "sent", "failed"}


def _error(code: str, status_code: int) -> HTTPException:
    messages = {"validation": "The request is invalid.", "not_found": "The resource was not found.",
                "conflict": "The resource is in a conflicting state."}
    return HTTPException(status_code=status_code, detail={"code": code, "message": messages[code]})


# -- n8n submission operations ----------------------------------------------


@router.post("/signals/refresh", status_code=202)
def signals_refresh(request: Request, _: None = Depends(require_n8n)) -> Response:
    """Re-score every asset's findings and create top-tier jobs; 202, no CSRF.

    Idempotent: a second refresh, or one while a refresh is in progress, creates
    no duplicate job (US-8). The daily schedule that drives this is task 38; the
    email delivery of the jobs is task 37.
    """
    factory: sessionmaker[Session] = request.app.state.session_factory
    kev = getattr(request.app.state, "kev_client", None)
    epss = getattr(request.app.state, "epss_client", None)
    with factory() as session:
        refresh_all(session, kev, epss)
        session.commit()
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post("/scans", status_code=202)
def scheduled_rescan(request: Request, _: None = Depends(require_n8n)) -> Response:
    """Start a re-scan of every registered asset asynchronously; 202, no CSRF."""
    factory: sessionmaker[Session] = request.app.state.session_factory
    worker = request.app.state.worker
    scan_ids: list[int] = []
    with factory() as session:
        for asset in session.scalars(select(Asset)):
            scan = enqueue_scan(session, asset, ScanTrigger.SCHEDULE)
            session.flush()
            scan_ids.append(scan.id)
        session.commit()
    if worker is not None:
        for scan_id in scan_ids:
            worker.enqueue(scan_id)
    return Response(status_code=status.HTTP_202_ACCEPTED)


# -- n8n showcase stubs (contract-only) -------------------------------------


@router.get("/notification-jobs")
def list_notification_jobs(request: Request, _: None = Depends(require_n8n)) -> list[dict[str, Any]]:
    # Showcase: the n8n delivery path is tasks 32-35. The backend delivers the
    # owner notification itself in submission scope, so this returns no jobs.
    kinds = request.query_params.getlist("kind")
    for kind in kinds:
        if kind not in _JOB_KINDS:
            raise _error("validation", 422)
    return []


@router.post("/notification-jobs/{job_id}/claim")
def claim_notification_job(job_id: str, request: Request, _: None = Depends(require_n8n)) -> dict[str, Any]:
    # Showcase stub: no job is ever listed, so any id is unknown.
    raise _error("not_found", 404)


@router.post("/notification-jobs/{job_id}/report", status_code=204)
def report_notification_job(job_id: str, request: Request, _: None = Depends(require_n8n)) -> Response:
    # Showcase stub: no job is ever claimable, so any id is unknown.
    raise _error("not_found", 404)


@router.get("/reports/weekly-digest")
def weekly_digest(request: Request, _: None = Depends(require_n8n)) -> dict[str, Any]:
    # Showcase stub: valid shape with no findings; validates the week query.
    week = request.query_params.get("week")
    if week is not None and not _WEEK_RE.match(week):
        raise _error("validation", 422)
    week = week or _current_iso_week()
    return {"week": week, "generatedAt": dt.datetime.now(dt.UTC).isoformat(), "findings": []}


def _current_iso_week() -> str:
    today = dt.datetime.now(dt.UTC).date()
    year, week, _ = today.isocalendar()
    return f"{year:04d}-W{week:02d}"


# -- responder submission operations ----------------------------------------


@router.get("/responder/findings/{finding_id}")
def responder_get_finding(
    finding_id: str, request: Request, _: None = Depends(require_responder)
) -> dict[str, Any]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        try:
            finding = session.get(Finding, int(finding_id))
        except (ValueError, TypeError):
            finding = None
        if finding is None:
            raise _error("not_found", 404)
        # The same FindingWithAsset as GET /findings/{id}; no advisory text is
        # carried by that shape, which is the responder's least-privilege view.
        return finding_to_wire(session, finding)


@router.get("/responder/notification-jobs")
def responder_list_jobs(
    request: Request, _: None = Depends(require_responder)
) -> list[dict[str, Any]]:
    finding_id = request.query_params.get("findingId")
    if not finding_id:  # required query; missing/empty -> 422
        raise _error("validation", 422)
    states = request.query_params.getlist("state")
    for state in states:
        if state not in _RESPONDER_STATES:
            raise _error("validation", 422)
    factory: sessionmaker[Session] = request.app.state.session_factory
    try:
        fid = int(finding_id)
    except (ValueError, TypeError):
        return []  # an unknown/!int findingId is a filter that matches nothing
    with factory() as session:
        finding = session.get(Finding, fid)
        if finding is None or finding.current_lifecycle_id is None:
            return []
        lifecycle_ids = list(
            session.scalars(select(Lifecycle.id).where(Lifecycle.finding_id == fid))
        )
        jobs = session.scalars(
            select(NotificationJob).where(NotificationJob.lifecycle_id.in_(lifecycle_ids))
        )
        rows = [_responder_job_to_wire(j, finding_id) for j in jobs]
        if states:
            rows = [r for r in rows if r["state"] in states]
        # createdAt desc, then id desc (string compare), a stable tie-break.
        rows.sort(key=lambda r: (r["createdAt"], r["id"]), reverse=True)
        return rows


def _responder_job_to_wire(job: NotificationJob, finding_id: str) -> dict[str, Any]:
    return {
        "id": str(job.id),
        "kind": job.kind,
        "state": job.state,
        "createdAt": job.created_at.isoformat() if job.created_at else None,
        "findingId": finding_id,
        "traceparent": job.traceparent,
        "attempts": job.attempts,
        "lastErrorCode": job.last_error_code,
    }


# -- MCP read operations (task 10b; Showcase US-12) -------------------------


@router.get("/mcp/top-exposures")
def mcp_top_exposures(request: Request, _: None = Depends(require_mcp)) -> list[dict[str, Any]]:
    """Up to `limit` open findings in server rank order, optionally one asset."""
    factory: sessionmaker[Session] = request.app.state.session_factory
    asset_id = request.query_params.get("assetId")
    limit = _validate_limit(request.query_params.get("limit"))
    with factory() as session:
        asset_pk: int | None = None
        if asset_id is not None:  # a 404 for an unknown asset (before limit work)
            try:
                asset_pk = int(asset_id)
            except (ValueError, TypeError):
                raise _error("not_found", 404) from None
            if session.get(Asset, asset_pk) is None:
                raise _error("not_found", 404)
        ordered = [f for f in ranked_findings(session) if f.status == "open"]
        if asset_pk is not None:
            ordered = [f for f in ordered if f.asset_id == asset_pk]
        return [
            ranked_finding_to_wire(session, finding, rank)
            for rank, finding in enumerate(ordered[:limit], start=1)
        ]


@router.get("/mcp/vulnerabilities/{vulnerability_id}/assets")
def mcp_which_assets(
    vulnerability_id: str, request: Request, _: None = Depends(require_mcp)
) -> dict[str, Any]:
    """Resolve any alias to its vulnerability and list every affected finding."""
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        alias = session.get(VulnerabilityAlias, vulnerability_id)
        vuln = session.get(Vulnerability, alias.vulnerability_id) if alias else None
        if vuln is None:  # unknown alias -> known: false, never 404
            return {"known": False, "untrustedAdvisoryData": None, "assets": []}
        aliases = sorted(
            session.scalars(
                select(VulnerabilityAlias.alias_id).where(
                    VulnerabilityAlias.vulnerability_id == vuln.id
                )
            )
        )
        findings = session.scalars(
            select(Finding).where(Finding.vulnerability_id == vuln.id).order_by(Finding.id)
        )
        assets = []
        for finding in findings:
            asset = session.get(Asset, finding.asset_id)
            assets.append({
                "assetId": str(finding.asset_id),
                "assetName": asset.name if asset else "",
                "findingId": str(finding.id),
                "status": finding.status,
                "tier": finding.tier,
            })
        return {
            "known": True,
            "untrustedAdvisoryData": {
                "label": UNTRUSTED_LABEL,
                "vulnerabilityId": vuln.identity_key,
                "aliases": aliases,
            },
            "assets": assets,
        }


@router.get("/mcp/findings/{finding_id}")
def mcp_get_finding(
    finding_id: str, request: Request, _: None = Depends(require_mcp)
) -> dict[str, Any]:
    """FindingWithAsset plus the labelled untrustedAdvisoryData (US-12)."""
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        try:
            finding = session.get(Finding, int(finding_id))
        except (ValueError, TypeError):
            finding = None
        if finding is None:
            raise _error("not_found", 404)
        wire = finding_to_wire(session, finding)
        wire["untrustedAdvisoryData"] = untrusted_advisory_data(session, finding.vulnerability_id)
        return wire


def _validate_limit(raw: str | None) -> int:
    if raw is None:
        return 10  # default
    try:
        value = int(raw)
    except (ValueError, TypeError):
        raise _error("validation", 422) from None
    if not (1 <= value <= 50):
        raise _error("validation", 422)
    return value
