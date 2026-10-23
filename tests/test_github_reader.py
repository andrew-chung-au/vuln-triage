"""U-GITHUB: the GitHub reader, replayed from fixtures through httpx.MockTransport."""

from __future__ import annotations

import logging

import httpx
import pytest

from github_stub import FixtureTransport
from network_guard import OutboundNetworkBlocked
from vulntriage.ingest.github import (
    GitHubReader,
    RepositoryUnavailable,
    split_repository_url,
)

SENTINEL = "ghp_SENTINEL_TOKEN_VALUE_123"
SHA = "1111111111111111111111111111111111111111"


def reader(stub: FixtureTransport, token: str | None = None) -> GitHubReader:
    return GitHubReader(stub.client(), token_provider=lambda: token)


def handler_reader(handler, token: str | None = None) -> GitHubReader:  # type: ignore[no-untyped-def]
    return GitHubReader(
        httpx.Client(transport=httpx.MockTransport(handler)), token_provider=lambda: token
    )


def test_resolves_branch_then_sha_then_reads_files_at_that_sha() -> None:
    stub = FixtureTransport()
    gh = reader(stub)
    sha = gh.resolve_commit("fixture-owner", "uv-app")
    assert sha == SHA
    text = gh.read_file("fixture-owner", "uv-app", SHA, "uv.lock")
    assert text is not None and text.startswith("version = 1")
    paths = [r.url.path for r in stub.requests]
    assert paths == [
        "/repos/fixture-owner/uv-app",
        "/repos/fixture-owner/uv-app/commits/main",
        "/repos/fixture-owner/uv-app/contents/uv.lock",
    ]
    assert stub.requests[-1].url.params["ref"] == SHA
    assert stub.requests[1].headers["accept"] == "application/vnd.github.sha"
    assert stub.requests[2].headers["accept"] == "application/vnd.github.raw+json"


def test_missing_file_is_absent_not_a_failure() -> None:
    gh = reader(FixtureTransport())
    assert gh.read_file("fixture-owner", "uv-app", SHA, "requirements.txt") is None


def test_directory_listing_is_absent() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"name": "x"}])

    assert handler_reader(handle).read_file("o", "r", SHA, "requirements.txt") is None


def test_empty_repository_has_no_commit() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/commits/main"):
            return httpx.Response(409, json={"message": "Git Repository is empty."})
        return httpx.Response(200, json={"default_branch": "main"})

    assert handler_reader(handle).resolve_commit("o", "r") is None


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500, 502, 301, 302])
def test_bad_repository_status_is_unavailable(status: int) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, headers={"location": "https://evil.example/"})

    with pytest.raises(RepositoryUnavailable):
        handler_reader(handle).resolve_commit("o", "r")


@pytest.mark.parametrize("status", [403, 429, 500, 301])
def test_bad_file_status_is_unavailable(status: int) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status)

    with pytest.raises(RepositoryUnavailable):
        handler_reader(handle).read_file("o", "r", SHA, "uv.lock")


@pytest.mark.parametrize("exc", [httpx.ConnectTimeout("t"), httpx.ReadTimeout("t"), httpx.ConnectError("c")])
def test_timeouts_and_transport_errors_are_unavailable(exc: Exception) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise exc

    with pytest.raises(RepositoryUnavailable):
        handler_reader(handle).resolve_commit("o", "r")


def test_malformed_repository_and_commit_answers_are_unavailable() -> None:
    def not_json(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>")

    def bad_sha(request: httpx.Request) -> httpx.Response:
        if "/commits/" in request.url.path:
            return httpx.Response(200, text="not-a-sha")
        return httpx.Response(200, json={"default_branch": "main"})

    with pytest.raises(RepositoryUnavailable):
        handler_reader(not_json).resolve_commit("o", "r")
    with pytest.raises(RepositoryUnavailable):
        handler_reader(bad_sha).resolve_commit("o", "r")


def test_only_get_and_only_api_github_com() -> None:
    stub = FixtureTransport()
    gh = reader(stub, token=SENTINEL)
    gh.resolve_commit("fixture-owner", "npm-app")
    gh.read_file("fixture-owner", "npm-app", "3" * 40, "package-lock.json")
    assert {r.method for r in stub.requests} == {"GET"}
    assert {r.url.host for r in stub.requests} == {"api.github.com"}
    assert {r.url.scheme for r in stub.requests} == {"https"}


@pytest.mark.parametrize(
    ("owner", "repo"),
    [("-bad", "r"), ("o/x", "r"), ("o", ".."), ("o", "r.git"), ("o", "a/b"), ("o", ""), ("o" * 40, "r"), ("o", "r\n")],
)
def test_invalid_owner_or_repo_raises_before_any_request(owner: str, repo: str) -> None:
    stub = FixtureTransport()
    gh = reader(stub)
    with pytest.raises(RepositoryUnavailable):
        gh.resolve_commit(owner, repo)
    with pytest.raises(RepositoryUnavailable):
        gh.read_file(owner, repo, SHA, "uv.lock")
    assert stub.requests == []


@pytest.mark.parametrize("path", ["../x.txt", "/etc/passwd", "a/../../b", "a?b", "a#b", "", "a\\b"])
def test_invalid_file_path_raises_before_any_request(path: str) -> None:
    stub = FixtureTransport()
    with pytest.raises(RepositoryUnavailable):
        reader(stub).read_file("fixture-owner", "uv-app", SHA, path)
    assert stub.requests == []


def test_is_readable_path_agrees_with_read_file() -> None:
    from vulntriage.ingest.github import is_readable_path

    for ok in ["uv.lock", "sub/a b.txt", "a@b+c=d,e~f-g_h.txt"]:
        assert is_readable_path(ok)
    for bad in ["cafü.txt", "a$b", "a%20b", "../x", "/x", "", "a\\b", "a//b"]:
        assert not is_readable_path(bad)


def test_oddly_named_path_still_raises_before_any_request() -> None:
    stub = FixtureTransport()
    with pytest.raises(RepositoryUnavailable):
        reader(stub).read_file("fixture-owner", "uv-app", SHA, "cafü/a$b%.txt")
    assert stub.requests == []


def test_redirect_is_not_followed() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(302, headers={"location": "https://evil.example/steal"})

    with pytest.raises(RepositoryUnavailable):
        handler_reader(handle, token=SENTINEL).resolve_commit("o", "r")
    assert len(seen) == 1


def test_authorization_header_only_when_a_token_is_set() -> None:
    without, with_token = FixtureTransport(), FixtureTransport()
    reader(without).resolve_commit("fixture-owner", "uv-app")
    reader(with_token, token=SENTINEL).resolve_commit("fixture-owner", "uv-app")
    assert all("authorization" not in r.headers for r in without.requests)
    assert all(r.headers["authorization"] == f"Bearer {SENTINEL}" for r in with_token.requests)


def test_token_never_appears_in_errors_or_logs(caplog: pytest.LogCaptureFixture) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"boom {request.headers['authorization']}")

    caplog.set_level(logging.DEBUG)
    with pytest.raises(RepositoryUnavailable) as info:
        handler_reader(handle, token=SENTINEL).resolve_commit("o", "r")
    assert SENTINEL not in str(info.value)
    assert SENTINEL not in repr(info.value)
    assert info.value.__cause__ is None and info.value.__context__ is not None
    assert SENTINEL not in caplog.text

    def error_body(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text=f"echo {request.headers['authorization']}")

    with pytest.raises(RepositoryUnavailable) as info2:
        handler_reader(error_body, token=SENTINEL).resolve_commit("o", "r")
    assert SENTINEL not in str(info2.value)


def test_default_client_fails_under_the_network_guard() -> None:
    with pytest.raises((OutboundNetworkBlocked, RepositoryUnavailable)):
        GitHubReader(token_provider=lambda: None).resolve_commit("octocat", "hello-world")


def test_recorder_refuses_unknown_sources_and_makes_no_request() -> None:
    import record_fixtures

    assert record_fixtures.main(["record_fixtures.py", "banana"]) == 2
    assert record_fixtures.main(["record_fixtures.py", "osv"]) == 2
    assert record_fixtures.main(["record_fixtures.py"]) == 2


def test_env_example_has_only_the_empty_token_name() -> None:
    from pathlib import Path

    text = (Path(__file__).resolve().parent.parent / ".env.example").read_text()
    assert text.strip() == "GITHUB_READ_TOKEN="


def test_split_repository_url() -> None:
    assert split_repository_url("https://github.com/o/r") == ("o", "r")
    for bad in ["http://github.com/o/r", "https://github.com/o/r.git", "https://github.com/o/r/", "https://github.com/o/r\n"]:
        assert split_repository_url(bad) is None
