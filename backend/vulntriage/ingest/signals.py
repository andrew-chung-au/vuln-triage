"""CISA KEV and FIRST EPSS enrichment (issue #78, task 6).

For every CVE that a finding's vulnerability carries, a per-CVE ``Signal`` row
records whether the CVE is in the CISA KEV catalogue and its FIRST EPSS score.
A vulnerability with no CVE (E11) gets no ``Signal``: the KEV value is derived as
``KEV: n/a (no CVE)`` and EPSS as ``n/a`` from ``Vulnerability.cve_id`` alone
(see :func:`vulntriage.db.enums.kev_value`).

Feed failure (E3) is handled here, and differs from an OSV outage: when KEV or
EPSS is unavailable while OSV succeeded, the last-known signal is kept and
marked stale (``kev_stale`` / ``epss_stale``); the scan status stays the OSV
result and is never ``scan failed``. A CVE that has never had a successful KEV
fetch keeps ``kev_listed`` null and the stale marker set, which derives to
``KEV: not listed`` with the stale marker (US-4, I15).

Reviewed source URLs (architecture.md § External data sources):
- CISA KEV: ``GET https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json``
- FIRST EPSS: ``GET https://api.first.org/data/v1/epss?cve=<comma-separated CVEs>``

Both clients take an injected ``httpx.Client`` so tests drive a ``MockTransport``
and make no live call (``U-NET``). Only these two hosts are contacted; redirects
are never followed.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from vulntriage.db.models import Finding, Signal, Vulnerability

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
KEV_HOST = "www.cisa.gov"
EPSS_BASE = "https://api.first.org/data/v1/epss"
EPSS_HOST = "api.first.org"
TIMEOUT_SECONDS = 10.0
RETRIES = 2  # total attempts = 1 + RETRIES
EPSS_BATCH = 100  # VERIFY: FIRST EPSS cve= batch size and rate limit


class FeedUnavailable(Exception):
    """A KEV or EPSS feed could not be fetched (E3: keep last-known, mark stale)."""


@dataclass(frozen=True)
class KevCatalogue:
    """The set of CVE ids in KEV and, per CVE, the date it was added."""

    date_added: dict[str, dt.date | None]

    def __contains__(self, cve_id: str) -> bool:
        return cve_id in self.date_added


@dataclass(frozen=True)
class EpssScore:
    cve_id: str
    score: float | None
    percentile: float | None
    date: dt.date | None


class KevClientProtocol(Protocol):
    def fetch_catalogue(self) -> KevCatalogue:
        ...


class EpssClientProtocol(Protocol):
    def fetch_scores(self, cve_ids: list[str]) -> dict[str, EpssScore]:
        ...


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _parse_date(value: Any) -> dt.date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return dt.date.fromisoformat(value[:10])
    except ValueError:
        return None


def _parse_float(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


class KevClient:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=False)

    def fetch_catalogue(self) -> KevCatalogue:
        response = _get(self._client, KEV_URL)
        if response.status_code != 200:
            raise FeedUnavailable(f"KEV {response.status_code}")
        data = _json(response, "KEV")
        vulns = data.get("vulnerabilities") if isinstance(data, dict) else None
        if not isinstance(vulns, list):
            raise FeedUnavailable("KEV: unexpected response shape")
        date_added: dict[str, dt.date | None] = {}
        for entry in vulns:
            if isinstance(entry, dict) and isinstance(entry.get("cveID"), str):
                date_added[entry["cveID"]] = _parse_date(entry.get("dateAdded"))
        return KevCatalogue(date_added)


class EpssClient:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=False)

    def fetch_scores(self, cve_ids: list[str]) -> dict[str, EpssScore]:
        scores: dict[str, EpssScore] = {}
        for start in range(0, len(cve_ids), EPSS_BATCH):
            chunk = cve_ids[start : start + EPSS_BATCH]
            response = _get(self._client, EPSS_BASE, params={"cve": ",".join(chunk)})
            if response.status_code != 200:
                raise FeedUnavailable(f"EPSS {response.status_code}")
            data = _json(response, "EPSS")
            rows = data.get("data") if isinstance(data, dict) else None
            if not isinstance(rows, list):
                raise FeedUnavailable("EPSS: unexpected response shape")
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get("cve"), str):
                    continue
                scores[row["cve"]] = EpssScore(
                    cve_id=row["cve"],
                    score=_parse_float(row.get("epss")),
                    percentile=_parse_float(row.get("percentile")),
                    date=_parse_date(row.get("date")),
                )
        return scores


def _get(client: httpx.Client, url: str, params: dict[str, str] | None = None) -> httpx.Response:
    for _attempt in range(1 + RETRIES):
        try:
            response = client.request(
                "GET", url, params=params, timeout=TIMEOUT_SECONDS, follow_redirects=False
            )
        except httpx.HTTPError:
            continue
        if response.status_code >= 500:
            continue
        return response
    raise FeedUnavailable("feed unavailable") from None


def _json(response: httpx.Response, feed: str) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        raise FeedUnavailable(f"{feed} returned invalid JSON") from exc


def _cve_ids_with_findings(session: Session, asset_id: int) -> list[str]:
    """The distinct CVE ids of the asset's findings' vulnerabilities, sorted."""
    rows = session.scalars(
        select(Vulnerability.cve_id)
        .join(Finding, Finding.vulnerability_id == Vulnerability.id)
        .where(Finding.asset_id == asset_id, Vulnerability.cve_id.is_not(None))
        .distinct()
    )
    return sorted({cve for cve in rows if cve})


def enrich_asset(
    session: Session,
    asset_id: int,
    kev_client: KevClientProtocol | None,
    epss_client: EpssClientProtocol | None,
) -> None:
    """Refresh KEV and EPSS signals for every CVE the asset's findings carry.

    KEV and EPSS are enriched independently: a failure of one keeps that feed's
    last-known values and sets its stale marker (E3), and never raises to the
    caller, so the scan status stays the OSV result. A vulnerability with no CVE
    gets no ``Signal`` (E11).
    """
    cve_ids = _cve_ids_with_findings(session, asset_id)
    if not cve_ids:
        return
    _enrich_kev(session, cve_ids, kev_client)
    _enrich_epss(session, cve_ids, epss_client)
    session.flush()


def _signal_for(session: Session, cve_id: str) -> Signal:
    signal = session.get(Signal, cve_id)
    if signal is None:
        signal = Signal(cve_id=cve_id)
        session.add(signal)
    return signal


def _enrich_kev(session: Session, cve_ids: list[str], client: KevClientProtocol | None) -> None:
    if client is None:
        return
    try:
        catalogue = client.fetch_catalogue()
    except FeedUnavailable:
        # Keep last-known values; mark stale (never fetched -> kev_listed stays null).
        for cve_id in cve_ids:
            _signal_for(session, cve_id).kev_stale = True
        return
    now = _now()
    for cve_id in cve_ids:
        signal = _signal_for(session, cve_id)
        listed = cve_id in catalogue
        signal.kev_listed = listed
        signal.kev_date_added = catalogue.date_added.get(cve_id) if listed else None
        signal.kev_fetched_at = now
        signal.kev_stale = False


def _enrich_epss(session: Session, cve_ids: list[str], client: EpssClientProtocol | None) -> None:
    if client is None:
        return
    try:
        scores = client.fetch_scores(cve_ids)
    except FeedUnavailable:
        for cve_id in cve_ids:
            _signal_for(session, cve_id).epss_stale = True
        return
    now = _now()
    for cve_id in cve_ids:
        signal = _signal_for(session, cve_id)
        score = scores.get(cve_id)
        if score is not None:
            signal.epss_score = score.score
            signal.epss_percentile = score.percentile
            signal.epss_date = score.date
        # A CVE absent from the EPSS answer keeps its last-known score; it is not
        # zeroed. Either way the fetch itself succeeded, so clear the stale mark.
        signal.epss_fetched_at = now
        signal.epss_stale = False
