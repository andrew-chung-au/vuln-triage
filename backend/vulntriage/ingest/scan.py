"""Scan ingestion: read the lockfiles, store dependencies and warnings (issue #76).

The ``Scan`` row is the job (D4): ``enqueue_scan`` creates it unfinished, and
``run_scan`` finishes it. A successful ingestion replaces the asset's
dependency set in one transaction; a failed one changes no dependency row.
OSV matching, findings and the audit trail belong to later tasks.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.db.enums import FailureReason, ScanStatus, ScanTrigger
from vulntriage.db.models import Asset, Dependency, Scan
from vulntriage.ingest.github import (
    RepositoryReader,
    RepositoryUnavailable,
    is_readable_path,
    split_repository_url,
)
from vulntriage.ingest.matcher import match_asset
from vulntriage.ingest.osv import FeedUnavailable, OsvClientProtocol
from vulntriage.ingest.ranking import rank_asset
from vulntriage.ingest.signals import EpssClientProtocol, KevClientProtocol, enrich_asset
from vulntriage.ingest.models import (
    INCLUDE_NOT_FOUND,
    INCLUDE_REFUSED,
    INCOMPLETE_KINDS,
    Entry,
    LockfileParseError,
    ScanWarning,
)
from vulntriage.ingest.package_lock import parse_package_lock
from vulntriage.ingest.requirements import parse_requirements, resolve_include
from vulntriage.ingest.uv_lock import parse_uv_lock

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_REQUIREMENT_FILES = 20
UV_LOCK = "uv.lock"
REQUIREMENTS = "requirements.txt"
PACKAGE_LOCK = "package-lock.json"


class ScanFailure(Exception):
    def __init__(self, reason: FailureReason) -> None:
        super().__init__(reason.value)
        self.reason = reason


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def new_trace_id() -> str:
    """A fresh 32-hex trace id (real OpenTelemetry ids arrive with task 23)."""
    return uuid.uuid4().hex


def enqueue_scan(session: Session, asset: Asset, trigger: ScanTrigger) -> Scan:
    """Add an unfinished ``Scan`` row for ``asset``; the caller commits.

    ``started_at`` means "enqueued" until the scan finishes (D4).
    """
    scan = Scan(
        asset_id=asset.id,
        trigger=trigger.value,
        started_at=_now(),
        finished_at=None,
        scan_status=ScanStatus.NOT_YET_SCANNED.value,
        failure_reason=None,
        warnings=[],
        trace_id=new_trace_id(),
    )
    session.add(scan)
    return scan


def unfinished_scan_ids(factory: sessionmaker[Session]) -> list[int]:
    with factory() as session:
        return list(
            session.scalars(select(Scan.id).where(Scan.finished_at.is_(None)).order_by(Scan.id))
        )


def _check_size(text: str) -> str:
    if len(text.encode("utf-8")) > MAX_FILE_BYTES:
        raise LockfileParseError("file too large")
    return text


def _read_and_parse(
    reader: RepositoryReader, repository_url: str
) -> tuple[str, list[Entry], list[ScanWarning]]:
    """Read and parse the three root files; raises ScanFailure or RepositoryUnavailable."""
    parts = split_repository_url(repository_url)
    if parts is None:
        raise RepositoryUnavailable("repository unavailable")
    owner, repo = parts
    sha = reader.resolve_commit(owner, repo)
    if sha is None:
        raise ScanFailure(FailureReason.NO_DEPENDENCY_FILES)

    uv_text = reader.read_file(owner, repo, sha, UV_LOCK)
    req_text = reader.read_file(owner, repo, sha, REQUIREMENTS)
    npm_text = reader.read_file(owner, repo, sha, PACKAGE_LOCK)
    if uv_text is None and req_text is None and npm_text is None:
        raise ScanFailure(FailureReason.NO_DEPENDENCY_FILES)

    entries: list[Entry] = []
    warnings: list[ScanWarning] = []
    if uv_text is not None:
        parsed = parse_uv_lock(_check_size(uv_text))
        entries += parsed.entries
        warnings += parsed.warnings
    if req_text is not None:
        _ingest_requirements(reader, owner, repo, sha, req_text, entries, warnings)
    if npm_text is not None:
        parsed = parse_package_lock(_check_size(npm_text))
        entries += parsed.entries
        warnings += parsed.warnings
    return sha, entries, warnings


def _ingest_requirements(
    reader: RepositoryReader,
    owner: str,
    repo: str,
    sha: str,
    root_text: str,
    entries: list[Entry],
    warnings: list[ScanWarning],
) -> None:
    """Parse requirements.txt and, breadth first, the in-repository ``-r`` includes."""
    seen = {REQUIREMENTS}
    queue: list[tuple[str, str]] = [(REQUIREMENTS, root_text)]
    while queue:
        name, text = queue.pop(0)
        result = parse_requirements(_check_size(text), name)
        entries += result.entries
        warnings += result.warnings
        for include in result.includes:
            target = resolve_include(name, include.target)
            if target is None:
                warnings.append(
                    ScanWarning(INCLUDE_REFUSED, name, include.line, "include refused")
                )
                continue
            if not is_readable_path(target):
                warnings.append(
                    ScanWarning(
                        INCLUDE_REFUSED,
                        name,
                        include.line,
                        "include refused: path has unsupported characters",
                    )
                )
                continue
            if target in seen:
                continue  # a file is read once; a cycle stops here
            if len(seen) >= MAX_REQUIREMENT_FILES:
                warnings.append(
                    ScanWarning(INCLUDE_REFUSED, name, include.line, "include limit reached")
                )
                continue
            seen.add(target)
            included = reader.read_file(owner, repo, sha, target)
            if included is None:
                warnings.append(
                    ScanWarning(
                        INCLUDE_NOT_FOUND, name, include.line, f"include not found: {target}"
                    )
                )
                continue
            queue.append((target, included))


def status_for_result(warnings: list[ScanWarning], has_findings: bool) -> ScanStatus:
    """The asset/scan status from the warnings and the OSV result (task 5, #77).

    ``scanned, findings`` whenever OSV matched at least one finding. Otherwise
    ``scanned, incomplete`` when any version-unknown or refused/missing-include
    warning exists (so "clean" is never claimed over an unscanned entry), else
    ``scanned, clean``.
    """
    if has_findings:
        return ScanStatus.SCANNED_FINDINGS
    if any(w.kind in INCOMPLETE_KINDS for w in warnings):
        return ScanStatus.SCANNED_INCOMPLETE
    return ScanStatus.SCANNED_CLEAN


def run_scan(
    factory: sessionmaker[Session],
    reader: RepositoryReader,
    scan_id: int,
    osv_client: OsvClientProtocol | None = None,
    kev_client: KevClientProtocol | None = None,
    epss_client: EpssClientProtocol | None = None,
) -> None:
    """Run one scan to completion. A scan that is already finished is left alone.

    ``osv_client`` matches the stored dependencies against OSV. When it is None
    no matching runs (the dependency ingestion still completes), which keeps the
    worker and the ingestion-only tests independent of an OSV stub.
    ``kev_client`` and ``epss_client`` enrich the resulting findings' CVEs with
    KEV and EPSS signals; a feed failure there marks signals stale and never
    changes the scan status (E3).
    """
    with factory() as session:
        scan = session.get(Scan, scan_id)
        if scan is None or scan.finished_at is not None:
            return
        asset = session.get(Asset, scan.asset_id)
        if asset is None:
            return
        try:
            sha, entries, warnings = _read_and_parse(reader, asset.repository_url)
        except RepositoryUnavailable:
            _fail(session, scan, asset, FailureReason.REPOSITORY_UNAVAILABLE)
            return
        except ScanFailure as failure:
            _fail(session, scan, asset, failure.reason)
            return
        except LockfileParseError:
            _fail(session, scan, asset, FailureReason.LOCKFILE_PARSE_ERROR)
            return

        now = _now()
        session.execute(delete(Dependency).where(Dependency.asset_id == asset.id))
        for entry in entries:
            session.add(
                Dependency(
                    asset_id=asset.id,
                    ecosystem=entry.ecosystem,
                    name=entry.name,
                    version=entry.version,
                    source_file=entry.source_file,
                    direct=entry.direct,
                )
            )
        session.flush()  # dependency ids are needed for the finding links

        has_findings = False
        if osv_client is not None:
            try:
                has_findings = match_asset(session, asset.id, osv_client)
            except FeedUnavailable:
                # E3: OSV unavailable on a scan is a feed failure, not a clean
                # result. On a first scan there are no findings to keep yet.
                session.rollback()
                scan = session.get(Scan, scan_id)
                asset = session.get(Asset, scan.asset_id)
                _fail(session, scan, asset, FailureReason.FEED_UNAVAILABLE)
                return
            # KEV/EPSS enrichment (E3): a feed failure here marks signals stale
            # and never raises, so it does not change the OSV scan status.
            enrich_asset(session, asset.id, kev_client, epss_client)
            # Deterministic ranking (task 7): score every finding from the
            # signals and asset context, replacing the placeholder rank fields.
            rank_asset(session, asset.id)

        status = status_for_result(warnings, has_findings)
        scan.warnings = [w.as_dict() for w in warnings]
        scan.scan_status = status.value
        scan.failure_reason = None
        scan.finished_at = now
        asset.scan_status = status.value
        asset.scan_failure_reason = None
        asset.last_scan_at = now
        asset.last_commit_sha = sha
        session.commit()


def _fail(session: Session, scan: Scan, asset: Asset, reason: FailureReason) -> None:
    """Record a failed scan; no dependency row is touched."""
    now = _now()
    scan.scan_status = ScanStatus.SCAN_FAILED.value
    scan.failure_reason = reason.value
    scan.finished_at = now
    asset.scan_status = ScanStatus.SCAN_FAILED.value
    asset.scan_failure_reason = reason.value
    asset.last_scan_at = now
    session.commit()


def run_pending_scans(
    factory: sessionmaker[Session],
    reader: RepositoryReader,
    osv_client: OsvClientProtocol | None = None,
    kev_client: KevClientProtocol | None = None,
    epss_client: EpssClientProtocol | None = None,
) -> int:
    """Run every unfinished scan in order, synchronously; return how many ran."""
    ids = unfinished_scan_ids(factory)
    for scan_id in ids:
        run_scan(factory, reader, scan_id, osv_client, kev_client, epss_client)
    return len(ids)
