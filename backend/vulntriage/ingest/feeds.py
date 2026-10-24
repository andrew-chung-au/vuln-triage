"""Production feed-source seam for the backend (task 40 / #172).

VulnTriage matches, enriches and ranks from four external feeds: OSV
(advisories), CISA KEV (known-exploited flag), FIRST EPSS (exploit-probability
score) and GitHub (repository reads). This module is the single place that
builds the four feed clients, in one of two modes:

- ``live``: each client talks to its real upstream over HTTP, exactly as
  :mod:`vulntriage.main` wires them today.
- ``fixtures``: each client is driven by an injected ``httpx.Client`` whose
  ``httpx.MockTransport`` replays the committed fixtures under
  ``tests/fixtures/`` with no network at all, so a deployed or Compose scan can
  run end to end offline.

The mode strings are :data:`vulntriage.ingest.settings.FEEDS_LIVE` and
``FEEDS_FIXTURES``; :func:`vulntriage.ingest.settings.require_feeds_allowed`
validates them and the environment gate at start-up.

Nothing in this module imports from ``tests/``: that is test-only code. The
replay handlers below are production reimplementations of the logic in the test
stubs (``tests/osv_stub.py``, ``tests/signals_stub.py``, ``tests/github_stub.py``),
ported verbatim as standalone functions so that fixtures mode is a first-class
production capability rather than a dependency on the test tree. The fixture
files themselves are shared between this module and the stubs; only the Python
handler code is duplicated.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
from typing import NamedTuple

import httpx

from vulntriage.ingest.github import GitHubReader
from vulntriage.ingest.osv import OsvClient
from vulntriage.ingest.settings import FEEDS_FIXTURES, FEEDS_LIVE, get_github_read_token
from vulntriage.ingest.signals import EpssClient, KevClient

# --- Fixtures root resolution ------------------------------------------------
# The env var wins when set (so a deployment can point at a mounted fixtures
# directory); otherwise default to the repo's tests/fixtures computed relative
# to this file: feeds.py -> ingest -> vulntriage -> backend -> repo root
# (parents[3]), then tests/fixtures.
_FIXTURES_ROOT_ENV = "VT_FIXTURES_ROOT"
_DEFAULT_FIXTURES_ROOT = pathlib.Path(__file__).resolve().parents[3] / "tests" / "fixtures"


def fixtures_root() -> pathlib.Path:
    """The directory the committed feed fixtures live in.

    ``VT_FIXTURES_ROOT`` overrides the default when set and non-empty; otherwise
    the repo's ``tests/fixtures`` directory, resolved relative to this file.
    """
    override = os.environ.get(_FIXTURES_ROOT_ENV)
    if override:
        return pathlib.Path(override)
    return _DEFAULT_FIXTURES_ROOT


# --- OSV replay (ports tests/osv_stub.py::OsvFixtureTransport._handle) --------

_OSV_VULN_PATH_RE = re.compile(r"/v1/vulns/([^/]+)")


def osv_fixture_client(root: pathlib.Path) -> httpx.Client:
    """An ``httpx.Client`` that replays ``<root>/osv/`` for :class:`OsvClient`.

    ``POST /v1/querybatch`` is answered from ``osv/querybatch.json``'s
    ``by_query`` map, keyed ``"<ecosystem>|<name>|<version>"``; an unknown query
    returns an empty ``vulns`` list (as the real OSV API does, not an error).
    ``GET /v1/vulns/{id}`` replays ``osv/vulns/<id>.json`` (404 when absent).
    """
    osv_root = root / "osv"
    by_query = json.loads((osv_root / "querybatch.json").read_text())["by_query"]

    def query_batch(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        results = []
        for query in body.get("queries", []):
            package = query.get("package", {})
            key = f"{package.get('ecosystem')}|{package.get('name')}|{query.get('version')}"
            results.append(by_query.get(key, {"vulns": []}))
        return httpx.Response(200, json={"results": results})

    def vuln(osv_id: str) -> httpx.Response:
        file = osv_root / "vulns" / f"{osv_id}.json"
        if not file.is_file():
            return httpx.Response(404, json={"code": 5, "message": "Not Found"})
        return httpx.Response(
            200, text=file.read_text(), headers={"content-type": "application/json"}
        )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v1/querybatch" and request.method == "POST":
            return query_batch(request)
        match = _OSV_VULN_PATH_RE.fullmatch(path)
        if match and request.method == "GET":
            return vuln(match.group(1))
        return httpx.Response(404, json={"code": 5, "message": "Not Found"})

    return httpx.Client(transport=httpx.MockTransport(handler))


# --- KEV replay (ports tests/signals_stub.py::KevFixtureTransport._handle) ----


def kev_fixture_client(root: pathlib.Path) -> httpx.Client:
    """An ``httpx.Client`` that replays the CISA KEV catalogue for :class:`KevClient`.

    Requests to host ``www.cisa.gov`` are answered with the whole committed
    catalogue at ``<root>/kev/known_exploited_vulnerabilities.json``; any other
    host gets a 404.
    """
    kev_file = root / "kev" / "known_exploited_vulnerabilities.json"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host != "www.cisa.gov":
            return httpx.Response(404)
        return httpx.Response(
            200, text=kev_file.read_text(), headers={"content-type": "application/json"}
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


# --- EPSS replay (ports tests/signals_stub.py::EpssFixtureTransport._handle) --


def epss_fixture_client(root: pathlib.Path) -> httpx.Client:
    """An ``httpx.Client`` that replays FIRST EPSS scores for :class:`EpssClient`.

    Requests to host ``api.first.org`` return only the rows for the CVEs named
    in the ``cve`` query parameter (as the real API does), read from
    ``<root>/epss/epss.json``'s ``data`` list; any other host gets a 404. The
    response shape matches the real API: ``{"status", "status-code", "total",
    "data"}``.
    """
    epss_file = root / "epss" / "epss.json"
    all_rows = {row["cve"]: row for row in json.loads(epss_file.read_text())["data"]}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host != "api.first.org":
            return httpx.Response(404)
        requested = request.url.params.get("cve", "")
        wanted = [c for c in requested.split(",") if c]
        data = [all_rows[c] for c in wanted if c in all_rows]
        return httpx.Response(
            200,
            json={"status": "OK", "status-code": 200, "total": len(data), "data": data},
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


# --- GitHub replay (ports tests/github_stub.py::FixtureTransport._handle) -----

_GITHUB_PATH_RE = re.compile(r"/repos/([^/]+)/([^/]+)(?:/(commits|contents)/(.+))?")


def github_fixture_client(root: pathlib.Path) -> httpx.Client:
    """An ``httpx.Client`` that replays ``<root>/github/`` for :class:`GitHubReader`.

    Per repository the layout is ``<owner>__<repo>/repo.json``, ``commit.txt``
    and ``contents/<path>`` (raw file text). A path that does not match the
    GitHub read pattern gets a plain 404; an unknown repository or missing file
    gets a 404 with a ``{"message": "Not Found"}`` body.
    """
    github_root = root / "github"

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        match = _GITHUB_PATH_RE.fullmatch(path)
        if not match:
            return httpx.Response(404)
        owner, repo, kind, rest = match.groups()
        folder = github_root / f"{owner}__{repo}"
        if not folder.is_dir():
            return httpx.Response(404, json={"message": "Not Found"})
        if kind is None:
            return httpx.Response(
                200,
                text=(folder / "repo.json").read_text(),
                headers={"content-type": "application/json"},
            )
        if kind == "commits":
            return httpx.Response(200, text=(folder / "commit.txt").read_text())
        file = folder / "contents" / rest
        if not file.is_file():
            return httpx.Response(404, json={"message": "Not Found"})
        return httpx.Response(
            200, text=file.read_text(), headers={"content-type": "text/plain"}
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


# --- The factory -------------------------------------------------------------


class FeedClients(NamedTuple):
    """The four feed clients a scan needs, built for one mode."""

    osv: OsvClient
    kev: KevClient
    epss: EpssClient
    reader: GitHubReader


def build_feed_clients(mode: str, root: pathlib.Path | None = None) -> FeedClients:
    """Build the OSV/KEV/EPSS/GitHub clients for ``mode``.

    ``mode`` is :data:`vulntriage.ingest.settings.FEEDS_LIVE` or
    ``FEEDS_FIXTURES`` (validate it with ``require_feeds_allowed`` at start-up).

    - ``live``: each client is built with no injected ``httpx.Client`` so it
      constructs its own live transport, exactly as ``main.py`` wires them. The
      reader defaults ``token_provider`` to
      :func:`vulntriage.ingest.settings.get_github_read_token`.
    - ``fixtures``: each client is driven by the matching fixture replay client
      from ``root`` (defaulting to :func:`fixtures_root`), and the reader is
      given a ``token_provider`` that always returns ``None`` (no token is used
      offline).

    Any other ``mode`` raises :class:`ValueError`.
    """
    if mode == FEEDS_LIVE:
        # Live: build each client with no injected transport; GitHubReader()
        # with no args matches how main.py constructs the live reader (it
        # defaults its own httpx.Client and token_provider=get_github_read_token).
        return FeedClients(
            osv=OsvClient(),
            kev=KevClient(),
            epss=EpssClient(),
            reader=GitHubReader(token_provider=get_github_read_token),
        )
    if mode == FEEDS_FIXTURES:
        resolved = root if root is not None else fixtures_root()
        return FeedClients(
            osv=OsvClient(osv_fixture_client(resolved)),
            kev=KevClient(kev_fixture_client(resolved)),
            epss=EpssClient(epss_fixture_client(resolved)),
            reader=GitHubReader(github_fixture_client(resolved), token_provider=lambda: None),
        )
    raise ValueError(
        f"unknown feeds mode {mode!r}; expected {FEEDS_LIVE!r} or {FEEDS_FIXTURES!r}"
    )
