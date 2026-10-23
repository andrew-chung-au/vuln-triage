"""Asset endpoints (issues #76, #82): register, list, read, update and re-scan.

``POST /assets`` (#76) now carries the session + ``security lead`` guard (#82),
alongside ``GET /assets``, ``GET /assets/{id}``, ``PATCH /assets/{id}`` and
``POST /assets/{id}/rescan``.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.api.security import may_accept_risk, require_session
from vulntriage.db.enums import ScanStatus, ScanTrigger, UserRole
from vulntriage.db.models import Asset, AuditEntry, User
from vulntriage.ingest.github import split_repository_url
from vulntriage.ingest.ranking import rank_asset
from vulntriage.ingest.scan import enqueue_scan
from vulntriage.worker import ScanWorker

router = APIRouter(tags=["assets"])

_EMAIL = re.compile(r"[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+")

_MESSAGES = {
    "not_found": "The resource was not found.",
    "forbidden": "The request is not allowed.",
    "validation": "The request is invalid.",
}


def _error(code: str, status_code: int) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": _MESSAGES[code]})


def _require_security_lead(user: User) -> None:
    if user.role != UserRole.SECURITY_LEAD.value:
        raise _error("forbidden", status.HTTP_403_FORBIDDEN)


def _lookup(session: Session, asset_id: str) -> Asset | None:
    try:
        return session.get(Asset, int(asset_id))
    except (ValueError, TypeError):
        return None


class NewAssetInput(BaseModel):
    """Strict body of ``POST /assets`` (``_docs/openapi.yaml``: NewAssetInput)."""

    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=False)

    name: str
    owner_name: str | None = Field(alias="ownerName")
    owner_email: str | None = Field(alias="ownerEmail")
    criticality: Literal["low", "medium", "high", "critical"]
    internet_facing: bool = Field(alias="internetFacing")
    repository_url: str = Field(alias="repositoryUrl")

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name is empty")
        return value

    @field_validator("owner_name")
    @classmethod
    def _owner_name(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None

    @field_validator("owner_email")
    @classmethod
    def _owner_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if not _EMAIL.fullmatch(value):
            raise ValueError("owner email is invalid")
        return value

    @field_validator("repository_url")
    @classmethod
    def _repository_url(cls, value: str) -> str:
        if split_repository_url(value) is None:
            raise ValueError("repository URL is invalid")
        return value


def asset_to_wire(asset: Asset, session: Session | None = None) -> dict[str, object]:
    """The contract ``Asset`` (camelCase).

    ``scanWarnings`` are the warnings of the asset's latest finished scan; empty
    until one finishes. A ``session`` is needed to read them (the ``POST``
    response, before any scan finishes, passes none and shows an empty list).
    """
    warnings: list[Any] = []
    if session is not None and asset.last_scan_at is not None:
        from vulntriage.db.models import Scan

        latest = session.scalar(
            select(Scan)
            .where(Scan.asset_id == asset.id, Scan.finished_at.is_not(None))
            .order_by(Scan.finished_at.desc(), Scan.id.desc())
        )
        if latest is not None and isinstance(latest.warnings, list):
            warnings = latest.warnings
    return {
        "id": str(asset.id),
        "name": asset.name,
        "ownerName": asset.owner_name,
        "ownerEmail": asset.owner_email,
        "criticality": asset.criticality,
        "internetFacing": asset.internet_facing,
        "repositoryUrl": asset.repository_url,
        "scanStatus": asset.scan_status,
        "scanFailureReason": asset.scan_failure_reason,
        "lastScanAt": asset.last_scan_at.isoformat() if asset.last_scan_at else None,
        "lastCommitSha": asset.last_commit_sha,
        "scanWarnings": warnings,
    }


def _parse_body(raw: bytes, model: type[BaseModel]) -> Any:
    """Validate a raw JSON body with ``model``, raising the contract 422 on failure."""
    from pydantic import ValidationError

    try:
        data = json.loads(raw) if raw else None
    except ValueError:
        raise _error("validation", 422) from None
    try:
        return model.model_validate(data)
    except ValidationError:
        raise _error("validation", 422) from None


@router.post("/assets", status_code=201)
async def create_asset(request: Request, user: User = Depends(require_session)) -> dict[str, object]:
    # registerAsset order: 401, CSRF 403 (both in require_session), then role
    # 403, then 422 — so the body is validated after the role check.
    _require_security_lead(user)
    body = _parse_body(await request.body(), NewAssetInput)

    factory: sessionmaker[Session] = request.app.state.session_factory
    worker: ScanWorker | None = request.app.state.worker
    with factory() as session:
        asset = Asset(
            name=body.name,
            owner_name=body.owner_name,
            owner_email=body.owner_email,
            criticality=body.criticality,
            internet_facing=body.internet_facing,
            repository_url=body.repository_url,
            scan_status=ScanStatus.NOT_YET_SCANNED.value,
        )
        session.add(asset)
        session.flush()
        scan = enqueue_scan(session, asset, ScanTrigger.REGISTRATION)
        session.commit()
        wire = asset_to_wire(asset, session)
        scan_id = scan.id
    if worker is not None:
        worker.enqueue(scan_id)
    return wire


@router.get("/assets")
def list_assets(request: Request, user: User = Depends(require_session)) -> list[dict[str, object]]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        assets = session.scalars(select(Asset).order_by(Asset.id))
        return [asset_to_wire(a, session) for a in assets]


@router.get("/assets/{asset_id}")
def get_asset(
    asset_id: str, request: Request, user: User = Depends(require_session)
) -> dict[str, object]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        asset = _lookup(session, asset_id)
        if asset is None:
            raise _error("not_found", status.HTTP_404_NOT_FOUND)
        return asset_to_wire(asset, session)


class AssetUpdateInput(BaseModel):
    """Strict body of ``PATCH /assets/{id}``: any of four fields, at least one.

    Which fields were sent is read from ``model_fields_set`` (by alias), so a
    field left out is "not provided" and an explicit ``null`` clears the value.
    """

    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=False)

    owner_name: str | None = Field(default=None, alias="ownerName")
    owner_email: str | None = Field(default=None, alias="ownerEmail")
    criticality: Literal["low", "medium", "high", "critical"] | None = Field(default=None)
    internet_facing: bool | None = Field(default=None, alias="internetFacing")

    @field_validator("owner_name")
    @classmethod
    def _owner_name(cls, value: str | None) -> str | None:
        return (value.strip() or None) if isinstance(value, str) else value

    @field_validator("owner_email")
    @classmethod
    def _owner_email(cls, value: str | None) -> str | None:
        if not isinstance(value, str):
            return value
        value = value.strip()
        if not value:
            return None
        if not _EMAIL.fullmatch(value):
            raise ValueError("owner email is invalid")
        return value

    def provided(self) -> dict[str, Any]:
        """Map of attr-name -> value for exactly the fields the body included.

        ``model_fields_set`` holds the attribute names of the fields present in
        the body (pydantic records them by field name, not alias).
        """
        return {name: getattr(self, name) for name in self.model_fields_set}


@router.patch("/assets/{asset_id}")
async def update_asset(
    asset_id: str, request: Request, user: User = Depends(require_session)
) -> dict[str, object]:
    # updateAsset order: 401, CSRF 403, 404, role 403, then 422.
    raw = await request.body()
    factory: sessionmaker[Session] = request.app.state.session_factory
    worker: ScanWorker | None = request.app.state.worker
    with factory() as session:
        asset = _lookup(session, asset_id)
        if asset is None:
            raise _error("not_found", status.HTTP_404_NOT_FOUND)
        _require_security_lead(user)
        body = _parse_body(raw, AssetUpdateInput)
        provided = body.provided()
        if not provided:  # minProperties: 1
            raise _error("validation", 422)

        changed = _apply_update(session, asset, provided, user)
        if changed:
            rank_asset(session, asset.id)  # criticality/exposure feed the tiers
            _release_held_jobs(session, asset)
        session.flush()
        wire = asset_to_wire(asset, session)
        session.commit()
        return wire


@router.post("/assets/{asset_id}/rescan", status_code=202)
async def rescan_asset(
    asset_id: str, request: Request, user: User = Depends(require_session)
) -> Response:
    # reScan order: 401, CSRF 403, 404, then owner-mismatch 403.
    factory: sessionmaker[Session] = request.app.state.session_factory
    worker: ScanWorker | None = request.app.state.worker
    with factory() as session:
        asset = _lookup(session, asset_id)
        if asset is None:
            raise _error("not_found", status.HTTP_404_NOT_FOUND)
        # A security lead may re-scan any asset; an asset owner only their own.
        if not may_accept_risk(user, asset.owner_email):
            raise _error("forbidden", status.HTTP_403_FORBIDDEN)
        scan = enqueue_scan(session, asset, ScanTrigger.PERSON)
        session.commit()
        scan_id = scan.id
    if worker is not None:
        worker.enqueue(scan_id)
    return Response(status_code=status.HTTP_202_ACCEPTED)


def _apply_update(session: Session, asset: Asset, provided: dict[str, Any], user: User) -> bool:
    """Apply only the provided fields; audit each real change. Returns whether anything changed."""
    field_names = {
        "owner_name": "ownerName",
        "owner_email": "ownerEmail",
        "criticality": "criticality",
        "internet_facing": "internetFacing",
    }
    changed = False
    for attr, value in provided.items():
        previous = getattr(asset, attr)
        if previous == value:
            continue  # setting a field to its current value changes nothing
        setattr(asset, attr, value)
        session.add(
            AuditEntry(
                finding_id=None,
                asset_id=asset.id,
                field=field_names[attr],
                previous_value=None if previous is None else str(previous),
                new_value="" if value is None else str(value),
                actor=str(user.id),
                source="dashboard",
            )
        )
        changed = True
    return changed


def _release_held_jobs(session: Session, asset: Asset) -> None:
    """Release ownerless / owner-email-missing jobs once the asset has an owner email.

    Submission scope has no notification jobs yet (tasks 10a/37), so this is a
    no-op placeholder that the delivery work will fill in. Kept here so the
    release point is explicit in the update path.
    """
    # Jobs and lifecycles that would be released are built in later tasks.
    return
