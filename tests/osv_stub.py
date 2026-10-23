"""An OSV API stub for tests: replays ``tests/fixtures/osv/`` through httpx.MockTransport.

``POST /v1/querybatch`` is answered from ``querybatch.json``'s ``by_query`` map,
keyed by ``"<ecosystem>|<name>|<version>"``; an unknown query returns an empty
``vulns`` list (OSV returns an empty result, not an error). ``GET /v1/vulns/{id}``
replays ``vulns/<id>.json``. Every request is recorded in ``self.requests`` so a
test can assert the exact calls and that no advisory is refetched.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "osv"


class OsvFixtureTransport:
    """Callable for httpx.MockTransport; records every request it sees."""

    def __init__(self, root: Path = FIXTURES) -> None:
        self.root = root
        self.requests: list[httpx.Request] = []
        self._by_query = json.loads((root / "querybatch.json").read_text())["by_query"]

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=self.transport())

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == "/v1/querybatch" and request.method == "POST":
            return self._query_batch(request)
        match = re.fullmatch(r"/v1/vulns/([^/]+)", path)
        if match and request.method == "GET":
            return self._vuln(match.group(1))
        return httpx.Response(404, json={"code": 5, "message": "Not Found"})

    def _query_batch(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        results = []
        for query in body.get("queries", []):
            package = query.get("package", {})
            key = f"{package.get('ecosystem')}|{package.get('name')}|{query.get('version')}"
            results.append(self._by_query.get(key, {"vulns": []}))
        return httpx.Response(200, json={"results": results})

    def _vuln(self, osv_id: str) -> httpx.Response:
        file = self.root / "vulns" / f"{osv_id}.json"
        if not file.is_file():
            return httpx.Response(404, json={"code": 5, "message": "Not Found"})
        return httpx.Response(200, text=file.read_text(), headers={"content-type": "application/json"})
