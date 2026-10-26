"""The GitHub client the real runner uses to remove a partial branch.

A run that ends as an error or as "no change" must leave no ``responder/<fp>``
branch on the remote. ``delete_branch_if_exists`` is the whole interface; tests
use ``fakes.FakeBranchClient`` or an ``httpx.MockTransport``.

VERIFY: GitHub REST ``GET /repos/{repo}/git/ref/heads/{branch}`` (404 if absent)
and ``DELETE /repos/{repo}/git/refs/heads/{branch}`` (204 on success).
"""

from __future__ import annotations

from typing import Protocol
from urllib.parse import quote

import httpx


class BranchClient(Protocol):
    def delete_branch_if_exists(self, branch: str) -> bool: ...


class GitHubRestBranches:
    def __init__(self, repo: str, token: str, *, transport: httpx.BaseTransport | None = None) -> None:
        self._repo = repo
        self._client = httpx.Client(
            base_url="https://api.github.com",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=20.0,
            transport=transport,
        )

    def delete_branch_if_exists(self, branch: str) -> bool:
        ref = quote(branch, safe="/")
        got = self._client.get(f"/repos/{self._repo}/git/ref/heads/{ref}")
        if got.status_code == 404:
            return False
        got.raise_for_status()
        self._client.delete(f"/repos/{self._repo}/git/refs/heads/{ref}").raise_for_status()
        return True
