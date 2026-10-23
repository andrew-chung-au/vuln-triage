"""``POST /assets``: register an asset and queue its first scan (issue #76).

OUT OF SCOPE here, owned by tasks 9a/9b (#81, #82): the session, CSRF and role
guard on this route, and ``GET /assets`` / ``GET /assets/{id}``. Until then the
route is unguarded (human decision D6); nothing is deployed before S1 ends.
"""

from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.db.enums import ScanStatus, ScanTrigger
from vulntriage.db.models import Asset
from vulntriage.ingest.github import split_repository_url
from vulntriage.ingest.scan import enqueue_scan
from vulntriage.worker import ScanWorker

router = APIRouter()

_EMAIL = re.compile(r"[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+")


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


def asset_to_wire(asset: Asset) -> dict[str, object]:
    """The contract ``Asset`` (camelCase). ``scanWarnings`` is empty until a scan finishes."""
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
        "scanWarnings": [],
    }


@router.post("/assets", status_code=201)
def create_asset(body: NewAssetInput, request: Request) -> dict[str, object]:
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
        wire = asset_to_wire(asset)
        scan_id = scan.id
    if worker is not None:
        worker.enqueue(scan_id)
    return wire
