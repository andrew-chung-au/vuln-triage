"""A GitHub API stub for tests: replays ``tests/fixtures/github/`` through httpx.MockTransport.

Layout per repository: ``<owner>__<repo>/repo.json``, ``commit.txt`` and
``contents/<path>`` (raw file text).
"""

from __future__ import annotations

import re
from pathlib import Path

import httpx

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "github"


class FixtureTransport:
    """Callable for httpx.MockTransport; records every request it sees."""

    def __init__(self, root: Path = FIXTURES) -> None:
        self.root = root
        self.requests: list[httpx.Request] = []

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=self.transport())

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        match = re.fullmatch(r"/repos/([^/]+)/([^/]+)(?:/(commits|contents)/(.+))?", path)
        if not match:
            return httpx.Response(404)
        owner, repo, kind, rest = match.groups()
        folder = self.root / f"{owner}__{repo}"
        if not folder.is_dir():
            return httpx.Response(404, json={"message": "Not Found"})
        if kind is None:
            return httpx.Response(200, text=(folder / "repo.json").read_text(),
                                  headers={"content-type": "application/json"})
        if kind == "commits":
            return httpx.Response(200, text=(folder / "commit.txt").read_text())
        file = folder / "contents" / rest
        if not file.is_file():
            return httpx.Response(404, json={"message": "Not Found"})
        return httpx.Response(200, text=file.read_text(), headers={"content-type": "text/plain"})
