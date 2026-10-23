"""Findings endpoints (issue #82, task 9b): list, read and accept risk.

All three require the session cookie (``require_session``, task 9a). Risk
acceptance follows the contract's error order exactly — ``404`` and the
owner-mismatch ``403`` come *before* body validation (``422``) — so the route
is async and reads/validates the body by hand after those checks, rather than
through a pydantic model, which FastAPI would validate first.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.api.security import may_accept_risk, require_session
from vulntriage.api.serializers import finding_to_wire
from vulntriage.db.enums import FindingStatus
from vulntriage.db.models import Asset, AuditEntry, Finding, User
from vulntriage.ingest.ranking import ranked_findings

router = APIRouter(tags=["findings"])

_MESSAGES = {
    "not_found": "The resource was not found.",
    "forbidden": "The request is not allowed.",
    "validation": "The request is invalid.",
    "conflict": "The resource is in a conflicting state.",
}


def _error(code: str, status_code: int) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": _MESSAGES[code]})


@router.get("/findings")
def list_findings(request: Request, user: User = Depends(require_session)) -> list[dict[str, Any]]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        return [finding_to_wire(session, f) for f in ranked_findings(session)]


@router.get("/findings/{finding_id}")
def get_finding(
    finding_id: str, request: Request, user: User = Depends(require_session)
) -> dict[str, Any]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        finding = _lookup(session, finding_id)
        if finding is None:
            raise _error("not_found", status.HTTP_404_NOT_FOUND)
        return finding_to_wire(session, finding)


@router.post("/findings/{finding_id}/risk-acceptance")
async def accept_risk(
    finding_id: str, request: Request, user: User = Depends(require_session)
) -> dict[str, Any]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    # Read the raw body up front, but validate it only after 404 and the owner
    # check, so the contract's error order (404, then 403, then 422) holds.
    raw = await request.body()

    with factory() as session:
        finding = _lookup(session, finding_id)
        if finding is None:
            raise _error("not_found", status.HTTP_404_NOT_FOUND)
        asset = session.get(Asset, finding.asset_id)
        if not may_accept_risk(user, asset.owner_email):
            raise _error("forbidden", status.HTTP_403_FORBIDDEN)

        reason = _validated_reason(raw)

        if finding.status != FindingStatus.OPEN.value:
            raise _error("conflict", status.HTTP_409_CONFLICT)

        previous = finding.status
        finding.status = FindingStatus.RISK_ACCEPTED.value
        session.add(
            AuditEntry(
                finding_id=finding.id,
                asset_id=None,
                field="status",
                previous_value=previous,
                new_value=FindingStatus.RISK_ACCEPTED.value,
                actor=str(user.id),
                source="dashboard",
                reason=reason,
            )
        )
        session.flush()
        wire = finding_to_wire(session, finding)
        session.commit()
        return wire


def _lookup(session: Session, finding_id: str) -> Finding | None:
    try:
        return session.get(Finding, int(finding_id))
    except (ValueError, TypeError):
        return None


def _validated_reason(raw: bytes) -> str:
    """Exactly ``{reason}`` with a non-empty, non-whitespace value, else 422."""
    try:
        body = json.loads(raw) if raw else None
    except ValueError:
        raise _error("validation", 422) from None
    if not isinstance(body, dict) or set(body) != {"reason"}:
        raise _error("validation", 422)
    reason = body.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise _error("validation", 422)
    return reason
