"""Read-only OSV client (issue #77; architecture.md § External data sources).

Two endpoints only, both without a key:
- ``POST https://api.osv.dev/v1/querybatch`` once per scan, with the batch of
  ``(ecosystem, name, version)`` queries, returning per-query vuln ids and
  their ``modified`` timestamps.
- ``GET https://api.osv.dev/v1/vulns/{id}`` for each advisory the caller does
  not already hold at the returned ``modified`` (the caller caches by id and
  ``modified``).

Limits, each enforced here: only these two ``api.osv.dev`` paths; redirects are
never followed; a 10 s timeout with two retries, after which
:class:`FeedUnavailable` is raised (E3). The client holds no credential. Like
the GitHub reader, the ``httpx.Client`` is injected so tests drive a
``MockTransport`` and no real request leaves the process.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

API_HOST = "api.osv.dev"
API_BASE = f"https://{API_HOST}"
TIMEOUT_SECONDS = 10.0
RETRIES = 2  # total attempts = 1 + RETRIES
MAX_BATCH = 1000  # VERIFY: OSV querybatch size limit

# OSV ids are short tokens (GHSA-…, CVE-…, PYSEC-…, GO-…, OSV-…): no path parts.
_OSV_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


class FeedUnavailable(Exception):
    """OSV could not be reached or answered badly (maps to ``feed unavailable``, E3)."""


@dataclass(frozen=True)
class Query:
    ecosystem: str
    name: str
    version: str


@dataclass(frozen=True)
class VulnRef:
    """One advisory id returned for a query, with its ``modified`` timestamp."""

    osv_id: str
    modified: str | None


class OsvClientProtocol(Protocol):
    def query_batch(self, queries: list[Query]) -> list[list[VulnRef]]:
        """Vuln refs per query, in the same order as ``queries``."""

    def get_vuln(self, osv_id: str) -> dict[str, Any]:
        """The full advisory for ``osv_id``."""


class OsvClient:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            timeout=TIMEOUT_SECONDS, follow_redirects=False
        )

    # -- request plumbing -------------------------------------------------

    def _request(self, method: str, path: str, json_body: Any | None = None) -> httpx.Response:
        last_error: Exception | None = None
        for _attempt in range(1 + RETRIES):
            try:
                response = self._client.request(
                    method,
                    f"{API_BASE}{path}",
                    json=json_body,
                    timeout=TIMEOUT_SECONDS,
                    follow_redirects=False,
                )
            except httpx.HTTPError as exc:
                last_error = exc
                continue
            if response.status_code >= 500:
                last_error = FeedUnavailable(f"OSV {response.status_code}")
                continue
            return response
        # No chaining: nothing from the failed request is carried on the exception.
        _ = last_error
        raise FeedUnavailable("OSV unavailable") from None

    # -- reads ------------------------------------------------------------

    def query_batch(self, queries: list[Query]) -> list[list[VulnRef]]:
        if not queries:
            return []
        if len(queries) > MAX_BATCH:
            raise FeedUnavailable(f"OSV batch too large: {len(queries)} > {MAX_BATCH}")
        body = {
            "queries": [
                {"package": {"ecosystem": q.ecosystem, "name": q.name}, "version": q.version}
                for q in queries
            ]
        }
        response = self._request("POST", "/v1/querybatch", body)
        if response.status_code != 200:
            raise FeedUnavailable(f"OSV querybatch {response.status_code}")
        data = _json(response)
        results = data.get("results")
        if not isinstance(results, list) or len(results) != len(queries):
            raise FeedUnavailable("OSV querybatch: unexpected response shape")
        return [_vuln_refs(result) for result in results]

    def get_vuln(self, osv_id: str) -> dict[str, Any]:
        if not _OSV_ID_RE.fullmatch(osv_id):
            raise FeedUnavailable(f"OSV vulns: refusing non-id {osv_id!r}")
        response = self._request("GET", f"/v1/vulns/{osv_id}")
        if response.status_code != 200:
            raise FeedUnavailable(f"OSV vulns/{osv_id} {response.status_code}")
        data = _json(response)
        if not isinstance(data, dict) or data.get("id") != osv_id:
            raise FeedUnavailable(f"OSV vulns/{osv_id}: unexpected response shape")
        return data


def _json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        raise FeedUnavailable("OSV returned invalid JSON") from exc


def _vuln_refs(result: Any) -> list[VulnRef]:
    if not isinstance(result, dict):
        return []
    vulns = result.get("vulns")
    if not isinstance(vulns, list):
        return []
    refs: list[VulnRef] = []
    for vuln in vulns:
        if isinstance(vuln, dict) and isinstance(vuln.get("id"), str):
            modified = vuln.get("modified")
            refs.append(VulnRef(vuln["id"], modified if isinstance(modified, str) else None))
    return refs
