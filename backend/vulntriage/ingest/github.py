"""Read-only GitHub repository reader (issue #76, ``U-GITHUB``).

Limits, each enforced here and tested: only ``GET``; only ``api.github.com``;
owner and repository are re-validated against the registration pattern before
any request; redirects are never followed (so the token cannot be sent
elsewhere); the token is sent only as an ``Authorization`` header and never
appears in an exception message.

VERIFY: the read shape is ``GET /repos/{o}/{r}`` (``default_branch``), then
``GET /repos/{o}/{r}/commits/{branch}`` with ``Accept: application/vnd.github.sha``
(409 for an empty repository), then ``GET /repos/{o}/{r}/contents/{path}?ref={sha}``
with ``Accept: application/vnd.github.raw+json``, plus the
``X-GitHub-Api-Version: 2022-11-28`` header.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, Protocol
from urllib.parse import quote

import httpx

from vulntriage.ingest.settings import get_github_read_token

API_HOST = "api.github.com"
API_BASE = f"https://{API_HOST}"
TIMEOUT_SECONDS = 10.0

# The pattern of _docs/openapi.yaml (NewAssetInput.repositoryUrl), kept case-sensitive.
OWNER_PATTERN = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})"
REPO_PATTERN = r"(?!\.{1,2}$)(?!.*\.git$)[A-Za-z0-9_.-]{1,100}"
REPOSITORY_URL_RE = re.compile(rf"https://github\.com/({OWNER_PATTERN})/({REPO_PATTERN})")
_OWNER_RE = re.compile(OWNER_PATTERN)
_REPO_RE = re.compile(REPO_PATTERN)
_SHA_RE = re.compile(r"[0-9a-f]{40}")
_PATH_RE = re.compile(r"[A-Za-z0-9_.@+=,~ -]+(?:/[A-Za-z0-9_.@+=,~ -]+)*")


def is_readable_path(path: str) -> bool:
    """Whether the reader would accept ``path`` (callers refuse the rest before reading)."""
    return bool(_PATH_RE.fullmatch(path)) and ".." not in path.split("/")


class RepositoryUnavailable(Exception):
    """The repository could not be read (maps to the failure reason of that name)."""


class RepositoryReader(Protocol):
    def resolve_commit(self, owner: str, repo: str) -> str | None:
        """The head commit SHA of the default branch; None for an empty repository."""

    def read_file(self, owner: str, repo: str, sha: str, path: str) -> str | None:
        """The file's text at ``sha``; None when the file is absent."""


def split_repository_url(url: str) -> tuple[str, str] | None:
    """(owner, repo) for a valid registration URL, else None."""
    match = REPOSITORY_URL_RE.fullmatch(url)
    return (match.group(1), match.group(2)) if match else None


class GitHubReader:
    def __init__(
        self,
        client: httpx.Client | None = None,
        token_provider: Callable[[], str | None] = get_github_read_token,
    ) -> None:
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=False)
        self._token_provider = token_provider

    # -- request plumbing -------------------------------------------------

    def _get(self, path: str, accept: str, params: dict[str, str] | None = None) -> httpx.Response:
        headers = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
        token = self._token_provider()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = self._client.request(
                "GET",
                f"{API_BASE}{path}",
                headers=headers,
                params=params,
                timeout=TIMEOUT_SECONDS,
                follow_redirects=False,
            )
        except httpx.HTTPError:
            # No chaining and no message: nothing from the request is carried on.
            raise RepositoryUnavailable("repository unavailable") from None
        return response

    @staticmethod
    def _check(owner: str, repo: str) -> str:
        if not (_OWNER_RE.fullmatch(owner) and _REPO_RE.fullmatch(repo)):
            raise RepositoryUnavailable("repository unavailable")
        return f"/repos/{owner}/{repo}"

    # -- reads ------------------------------------------------------------

    def get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        base = self._check(owner, repo)
        response = self._get(base, "application/vnd.github+json")
        if response.status_code != 200:
            raise RepositoryUnavailable("repository unavailable")
        try:
            data = json.loads(response.text)
        except ValueError:
            raise RepositoryUnavailable("repository unavailable") from None
        if not isinstance(data, dict):
            raise RepositoryUnavailable("repository unavailable")
        return data

    def resolve_commit(self, owner: str, repo: str) -> str | None:
        base = self._check(owner, repo)
        branch = self.get_repository(owner, repo).get("default_branch")
        if not isinstance(branch, str) or not branch or ".." in branch.split("/"):
            raise RepositoryUnavailable("repository unavailable")
        response = self._get(
            f"{base}/commits/{quote(branch, safe='/')}", "application/vnd.github.sha"
        )
        if response.status_code == 409:  # VERIFY: an empty repository answers 409
            return None
        sha = response.text.strip()
        if response.status_code != 200 or not _SHA_RE.fullmatch(sha):
            raise RepositoryUnavailable("repository unavailable")
        return sha

    def read_file(self, owner: str, repo: str, sha: str, path: str) -> str | None:
        base = self._check(owner, repo)
        if not _SHA_RE.fullmatch(sha) or not is_readable_path(path):
            raise RepositoryUnavailable("repository unavailable")
        response = self._get(
            f"{base}/contents/{quote(path, safe='/')}",
            "application/vnd.github.raw+json",
            params={"ref": sha},
        )
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise RepositoryUnavailable("repository unavailable")
        # A directory comes back as a JSON listing, not as raw text: treat it as absent.
        if response.headers.get("content-type", "").startswith("application/json"):
            return None
        return response.content.decode("utf-8", errors="replace")
