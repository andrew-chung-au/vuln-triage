"""KEV and EPSS API stubs for tests: replay ``tests/fixtures/{kev,epss}/`` via httpx.MockTransport.

``KevFixtureTransport`` answers the CISA KEV URL with the whole committed
catalogue. ``EpssFixtureTransport`` answers the FIRST EPSS URL, returning only
the rows for the CVEs named in the ``cve`` query parameter (as the real API
does). Both record every request in ``self.requests`` so a test can assert the
calls and the hosts. A ``fail=True`` transport answers 503 to exercise E3.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

FIXTURES = Path(__file__).resolve().parent / "fixtures"
KEV_FILE = FIXTURES / "kev" / "known_exploited_vulnerabilities.json"
EPSS_FILE = FIXTURES / "epss" / "epss.json"


class KevFixtureTransport:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.requests: list[httpx.Request] = []

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=self.transport())

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.fail:
            return httpx.Response(503)
        if request.url.host != "www.cisa.gov":
            return httpx.Response(404)
        return httpx.Response(200, text=KEV_FILE.read_text(),
                              headers={"content-type": "application/json"})


class EpssFixtureTransport:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.requests: list[httpx.Request] = []
        self._all = {row["cve"]: row for row in json.loads(EPSS_FILE.read_text())["data"]}

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=self.transport())

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.fail:
            return httpx.Response(503)
        if request.url.host != "api.first.org":
            return httpx.Response(404)
        requested = request.url.params.get("cve", "")
        wanted = [c for c in requested.split(",") if c]
        data = [self._all[c] for c in wanted if c in self._all]
        return httpx.Response(
            200,
            json={"status": "OK", "status-code": 200, "total": len(data), "data": data},
        )
