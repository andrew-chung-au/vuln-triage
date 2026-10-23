"""Wire serialisers for findings and audit entries (issue #82, task 9b).

The ``Finding``/``FindingWithAsset`` wire shape (``_docs/openapi.yaml``) joins a
finding with its vulnerability (aliases, CVE), its per-CVE KEV/EPSS signal
(derived, not stored), its dependency entries, a read-only projection of the
merged advisories' affected ranges, its audit trail, and its asset. Briefs are
Showcase and not built for submission, so ``briefStatus`` is always ``pending``
and ``brief`` is ``null``.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vulntriage.api.assets import asset_to_wire
from vulntriage.db.enums import kev_value
from vulntriage.db.models import (
    Advisory,
    Asset,
    AuditEntry,
    Dependency,
    Finding,
    FindingDependency,
    Signal,
    User,
    Vulnerability,
    VulnerabilityAlias,
)


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def audit_to_wire(session: Session, entry: AuditEntry) -> dict[str, Any]:
    display_name: str | None = None
    if entry.actor not in ("re-scan", "system"):
        try:
            user = session.get(User, int(entry.actor))
            display_name = user.display_name if user is not None else None
        except (ValueError, TypeError):
            display_name = None
    return {
        "id": str(entry.id),
        "actor": entry.actor,
        "actorDisplayName": display_name,
        "createdAt": _iso(entry.created_at),
        "field": entry.field,
        "previousValue": entry.previous_value,
        "newValue": entry.new_value,
        "reason": entry.reason,
        "source": entry.source,
        "restoresEntryId": str(entry.restores_entry_id) if entry.restores_entry_id else None,
    }


def _affected_ranges(advisories: list[Advisory], ecosystem: str, package: str) -> list[dict[str, Any]]:
    """A read-only projection of the merged advisories' ranges for this package.

    It does not say which range contains the installed version; it lists each
    affected range as OSV reports it with the range's own fixed value. Advisory
    text is untrusted and only stored, never interpreted as instructions.
    """
    out: list[dict[str, Any]] = []
    for advisory in advisories:
        for entry in advisory.affected or []:
            if not isinstance(entry, dict):
                continue
            pkg = entry.get("package", {})
            if not isinstance(pkg, dict):
                continue
            if pkg.get("ecosystem") != ecosystem or str(pkg.get("name", "")).lower() != package.lower():
                continue
            for osv_range in entry.get("ranges", []) or []:
                if not isinstance(osv_range, dict):
                    continue
                introduced: str | None = None
                for event in osv_range.get("events", []) or []:
                    if not isinstance(event, dict):
                        continue
                    if "introduced" in event:
                        introduced = str(event["introduced"])
                    elif "fixed" in event:
                        out.append({"range": _range_text(introduced, event["fixed"], False),
                                    "fixedVersion": str(event["fixed"])})
                        introduced = None
                    elif "last_affected" in event:
                        out.append({"range": _range_text(introduced, event["last_affected"], True),
                                    "fixedVersion": None})
                        introduced = None
                if introduced is not None:  # open-ended
                    out.append({"range": _range_text(introduced, None, False), "fixedVersion": None})
            for version in entry.get("versions", []) or []:
                if isinstance(version, str):
                    out.append({"range": f"=={version}", "fixedVersion": None})
    return out


def _range_text(introduced: str | None, upper: Any, inclusive: bool) -> str:
    lower = "0" if introduced in (None, "0") else str(introduced)
    if upper is None:
        return f">={lower}"
    close = "<=" if inclusive else "<"
    return f">={lower},{close}{upper}"


def finding_to_wire(session: Session, finding: Finding, *, with_asset: bool = True) -> dict[str, Any]:
    vuln = session.get(Vulnerability, finding.vulnerability_id)
    aliases = sorted(
        session.scalars(
            select(VulnerabilityAlias.alias_id).where(
                VulnerabilityAlias.vulnerability_id == vuln.id
            )
        )
    )
    signal = session.get(Signal, vuln.cve_id) if vuln.cve_id else None
    advisories = list(
        session.scalars(select(Advisory).where(Advisory.vulnerability_id == vuln.id))
    )
    dep_ids = session.scalars(
        select(FindingDependency.dependency_id).where(
            FindingDependency.finding_id == finding.id
        )
    )
    dependencies = [
        {"version": d.version, "sourceFile": d.source_file, "direct": d.direct}
        for d in (session.get(Dependency, did) for did in dep_ids)
        if d is not None
    ]
    audit_trail = [
        audit_to_wire(session, e)
        for e in session.scalars(
            select(AuditEntry).where(AuditEntry.finding_id == finding.id).order_by(AuditEntry.id)
        )
    ]

    kev = kev_value(vuln.cve_id, signal.kev_listed if signal else None).value
    wire: dict[str, Any] = {
        "id": str(finding.id),
        "vulnerabilityId": vuln.identity_key,
        "aliases": aliases,
        "cveId": vuln.cve_id,
        "tier": finding.tier,
        "assetId": str(finding.asset_id),
        "package": finding.package,
        "ecosystem": finding.ecosystem,
        "dependencies": dependencies,
        "fixedVersion": finding.fixed_version,
        "affectedRanges": _affected_ranges(advisories, finding.ecosystem, finding.package),
        "kev": kev,
        "kevStale": bool(signal.kev_stale) if signal else False,
        "epss": signal.epss_score if signal else None,
        "epssStale": bool(signal.epss_stale) if signal else False,
        "status": finding.status,
        "firstDetectedAt": _iso(finding.first_detected_at),
        "fixedAt": _iso(finding.fixed_at),
        "stale": bool(finding.stale),
        "staleSince": _iso(finding.stale_since),
        "signalsChanged": bool(finding.signals_changed),
        "statusBeforeWithdrawal": finding.status_before_withdrawal,
        "rankReason": finding.rank_reason,
        "briefStatus": "pending",  # briefs are Showcase; not built for submission
        "brief": None,
        "auditTrail": audit_trail,
    }
    if with_asset:
        wire["asset"] = asset_to_wire(session.get(Asset, finding.asset_id), session)
    return wire
