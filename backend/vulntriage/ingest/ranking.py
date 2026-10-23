"""Deterministic, explainable ranking (issue #79, task 7).

No AI: the tier is one of four fixed rules applied top to bottom, the first match
winning, and the order within and across tiers is total. The rule inputs and the
chosen rule are recorded on each finding as ``tier``, ``rank_inputs`` and
``rank_reason`` (US-5), so re-scoring the same inputs always gives the same
result and every rank carries its reason.

All values are from ``_docs/architecture.md`` § Prioritisation:
- T = 0.10 (A18); "EPSS high" means the EPSS score is >= T.
- "exposed" means the asset is internet-facing or its criticality is ``critical``
  (A17: only ``critical`` counts as critical).
- "fix available" means the finding has a fixed version for this dependency.
- Tiers: P1 = KEV listed and exposed; P2 = KEV listed (not exposed) or EPSS high
  on an exposed asset; P3 = fix available and not P1/P2; P4 = everything else.
- Total order: EPSS higher first (``n/a`` after every scored finding), then
  criticality ``critical`` > ``high`` > ``medium`` > ``low``, then older
  ``first_detected_at`` first, then finding id ascending.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vulntriage.db.enums import Criticality, FindingStatus, KevValue, Tier, kev_value
from vulntriage.db.models import Finding, Signal, Vulnerability

_TIER_SEVERITY = {Tier.P1.value: 0, Tier.P2.value: 1, Tier.P3.value: 2, Tier.P4.value: 3}

EPSS_HIGH_THRESHOLD = 0.10  # A18

# Criticality order for the tie-break: critical first (highest).
_CRITICALITY_ORDER = {
    Criticality.CRITICAL.value: 0,
    Criticality.HIGH.value: 1,
    Criticality.MEDIUM.value: 2,
    Criticality.LOW.value: 3,
}


@dataclass(frozen=True)
class RankInputs:
    """The signals that feed the tier rules and the tie-break, for one finding."""

    kev: str  # the derived KEV value string
    epss: float | None  # the EPSS score, or None for n/a
    fix_available: bool
    internet_facing: bool
    criticality: str

    @property
    def exposed(self) -> bool:
        return self.internet_facing or self.criticality == Criticality.CRITICAL.value

    @property
    def kev_listed(self) -> bool:
        return self.kev == KevValue.LISTED.value

    @property
    def epss_high(self) -> bool:
        return self.epss is not None and self.epss >= EPSS_HIGH_THRESHOLD

    def as_dict(self) -> dict[str, Any]:
        return {
            "kev": self.kev,
            "epss": self.epss,
            "fixAvailable": self.fix_available,
            "internetFacing": self.internet_facing,
            "criticality": self.criticality,
            "exposed": self.exposed,
        }


def tier_for(inputs: RankInputs) -> tuple[Tier, str]:
    """The tier and a plain-language rank reason; the first matching rule wins."""
    signals = _signal_phrase(inputs)
    if inputs.kev_listed and inputs.exposed:
        return Tier.P1, f"P1: KEV listed and exposed asset; {signals}"
    if inputs.kev_listed:
        return Tier.P2, f"P2: KEV listed, asset not exposed; {signals}"
    if inputs.epss_high and inputs.exposed:
        return Tier.P2, f"P2: EPSS high on an exposed asset; {signals}"
    if inputs.fix_available:
        return Tier.P3, f"P3: fix available, no exploitation evidence; {signals}"
    return Tier.P4, f"P4: no fix available, no exploitation evidence; {signals}"


def _signal_phrase(inputs: RankInputs) -> str:
    epss = "n/a" if inputs.epss is None else f"{inputs.epss:.2f}"
    facing = "internet-facing" if inputs.internet_facing else "not internet-facing"
    fix = "fix available" if inputs.fix_available else "no fixed version"
    return f"{inputs.kev}; EPSS {epss}; {facing}, criticality {inputs.criticality}; {fix}"


def sort_key(inputs: RankInputs, first_detected_at: dt.datetime, finding_id: int) -> tuple:
    """A total-order key: EPSS desc (n/a last), criticality, age, id ascending."""
    has_epss = 0 if inputs.epss is not None else 1  # scored findings sort first
    epss_desc = -(inputs.epss or 0.0)  # higher EPSS first
    criticality_rank = _CRITICALITY_ORDER.get(inputs.criticality, len(_CRITICALITY_ORDER))
    return (has_epss, epss_desc, criticality_rank, first_detected_at, finding_id)


def _inputs_for(finding: Finding, vuln: Vulnerability, signal: Signal | None,
                internet_facing: bool, criticality: str) -> RankInputs:
    kev_listed = signal.kev_listed if signal is not None else None
    kev = kev_value(vuln.cve_id, kev_listed).value
    epss = signal.epss_score if signal is not None else None
    return RankInputs(
        kev=kev,
        epss=epss,
        fix_available=finding.fixed_version is not None,
        internet_facing=internet_facing,
        criticality=criticality,
    )


def _escalated(prev_tier: str, new_tier: str, prev_kev: str | None, new_kev: str) -> bool:
    """E8: the tier rose (a lower severity number) or KEV changed to listed."""
    tier_rose = _TIER_SEVERITY.get(new_tier, 9) < _TIER_SEVERITY.get(prev_tier, 9)
    kev_newly_listed = new_kev == KevValue.LISTED.value and prev_kev != KevValue.LISTED.value
    return tier_rose or kev_newly_listed


def rank_asset(session: Session, asset_id: int) -> None:
    """Score every finding of ``asset_id`` (A20: ``open`` and ``risk accepted``).

    Reads the finding's vulnerability CVE, the per-CVE ``Signal`` and the asset's
    exposure, then writes ``tier``, ``rank_inputs`` and ``rank_reason``. Called
    inside the scan transaction after KEV/EPSS enrichment, and re-run whenever the
    inputs change (a re-scan, or a criticality/exposure change).
    """
    from vulntriage.db.models import Asset

    asset = session.get(Asset, asset_id)
    if asset is None:
        return
    findings = list(session.scalars(select(Finding).where(Finding.asset_id == asset_id)))
    for finding in findings:
        vuln = session.get(Vulnerability, finding.vulnerability_id)
        signal = session.get(Signal, vuln.cve_id) if vuln.cve_id else None
        inputs = _inputs_for(finding, vuln, signal, asset.internet_facing, asset.criticality)
        tier, reason = tier_for(inputs)
        previous_tier = finding.tier
        previous_kev = (finding.rank_inputs or {}).get("kev")
        finding.tier = tier.value
        finding.rank_inputs = inputs.as_dict()
        finding.rank_reason = reason
        # E8: a risk-accepted finding whose signals escalate (the tier rises or
        # KEV becomes listed) keeps its status but is flagged "signals changed".
        if finding.status == FindingStatus.RISK_ACCEPTED.value and _escalated(
            previous_tier, tier.value, previous_kev, inputs.kev
        ):
            finding.signals_changed = True


@dataclass(frozen=True)
class RankedFinding:
    """A finding paired with its order key, for building a ranked list."""

    finding_id: int
    inputs: RankInputs
    first_detected_at: dt.datetime


def order_findings(items: list[RankedFinding]) -> list[int]:
    """Return finding ids in rank order (tier first, then the within-tier key)."""
    tier_rank = {Tier.P1.value: 0, Tier.P2.value: 1, Tier.P3.value: 2, Tier.P4.value: 3}

    def key(item: RankedFinding) -> tuple:
        tier, _ = tier_for(item.inputs)
        return (tier_rank[tier.value],) + sort_key(
            item.inputs, item.first_detected_at, item.finding_id
        )

    return [item.finding_id for item in sorted(items, key=key)]
