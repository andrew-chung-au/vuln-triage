"""OSV client (issue #77): request shape, the two endpoints only, and feed failure (E3)."""

from __future__ import annotations

import httpx
import pytest

from osv_stub import OsvFixtureTransport
from vulntriage.ingest.osv import FeedUnavailable, OsvClient, Query

pytestmark = pytest.mark.unit


def test_query_batch_sends_one_post_with_every_query() -> None:
    stub = OsvFixtureTransport()
    client = OsvClient(stub.client())
    queries = [Query("PyPI", "urllib3", "1.26.9"), Query("PyPI", "requests", "2.28.2")]

    results = client.query_batch(queries)

    assert len(stub.requests) == 1
    request = stub.requests[0]
    assert request.method == "POST"
    assert str(request.url) == "https://api.osv.dev/v1/querybatch"
    assert [ref.osv_id for ref in results[0]] == ["GHSA-v845-jxx5-vc9f", "PYSEC-2023-212"]
    assert results[1] == []  # requests 2.28.2 is clean: empty vulns, not an error


def test_get_vuln_reads_the_advisory_by_id() -> None:
    stub = OsvFixtureTransport()
    client = OsvClient(stub.client())
    advisory = client.get_vuln("GHSA-v845-jxx5-vc9f")
    assert advisory["id"] == "GHSA-v845-jxx5-vc9f"
    assert "CVE-2023-43804" in advisory["aliases"]
    assert str(stub.requests[-1].url) == "https://api.osv.dev/v1/vulns/GHSA-v845-jxx5-vc9f"


def test_empty_query_list_makes_no_request() -> None:
    stub = OsvFixtureTransport()
    client = OsvClient(stub.client())
    assert client.query_batch([]) == []
    assert stub.requests == []


def test_unknown_query_returns_empty_not_error() -> None:
    stub = OsvFixtureTransport()
    client = OsvClient(stub.client())
    assert client.query_batch([Query("PyPI", "never-heard-of-it", "1.0.0")]) == [[]]


def test_get_vuln_refuses_a_non_id_path() -> None:
    stub = OsvFixtureTransport()
    client = OsvClient(stub.client())
    with pytest.raises(FeedUnavailable):
        client.get_vuln("../../etc/passwd")
    assert stub.requests == []  # nothing left the client


def test_server_error_retries_then_raises_feed_unavailable() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503)

    client = OsvClient(httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(FeedUnavailable):
        client.query_batch([Query("PyPI", "pkg", "1.0.0")])
    assert calls["n"] == 3  # 1 attempt + 2 retries


def test_connect_error_raises_feed_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route")

    client = OsvClient(httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(FeedUnavailable):
        client.get_vuln("GHSA-0000-0000-0000")
