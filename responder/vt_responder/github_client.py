"""The GitHub client the real runner uses to look after ``responder/<fp>`` branches.

A run that ends as an error or as "no change" must not leave a ``responder/<fp>``
branch it created on the remote, and must never delete one it did not create.
The runner records ``get_branch_sha`` before the session, compares it afterwards
and only then calls ``delete_branch_if_exists``; after the session it reads the
reported pull request with ``get_pull_request`` (#244). Tests use
``fakes.FakeBranchClient`` or an ``httpx.MockTransport``.

Every method re-checks the branch name itself (``responder/`` plus a safe
fingerprint) so a raw or hostile string can never reach a URL.

VERIFY: GitHub REST ``GET /repos/{repo}/git/ref/heads/{branch}`` (404 if absent,
``object.sha`` is the head), ``DELETE /repos/{repo}/git/refs/heads/{branch}`` (204
on success) and ``GET /repos/{repo}/pulls/{number}`` (``head.ref``, ``head.repo.full_name``).
"""

from __future__ import annotations

from typing import Any, Protocol
from urllib.parse import quote

import httpx

from .policy import BRANCH_PREFIX, SAFE_ID


class BranchClient(Protocol):
    def get_branch_sha(self, branch: str) -> str | None: ...
    def get_pull_request(self, number: int) -> dict[str, Any] | None: ...
    def delete_branch_if_exists(self, branch: str) -> bool: ...


def checked_branch(branch: str) -> str:
    """The branch name if it is exactly ``responder/<safe fingerprint>``, else ``ValueError``."""
    if (not isinstance(branch, str) or not branch.startswith(BRANCH_PREFIX)
            or not SAFE_ID.fullmatch(branch[len(BRANCH_PREFIX):])):
        raise ValueError("not a responder branch")
    return branch


class GitHubRestBranches:
    def __init__(self, repo: str, token: str, *, transport: httpx.BaseTransport | None = None) -> None:
        self._repo = repo
        self._client = httpx.Client(
            base_url="https://api.github.com",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=20.0,
            transport=transport,
        )

    @staticmethod
    def _ref(branch: str) -> str:
        # The name was just validated; the fingerprint part is still quoted with safe="".
        checked = checked_branch(branch)
        return BRANCH_PREFIX.rstrip("/") + "/" + quote(checked[len(BRANCH_PREFIX):], safe="")

    def get_branch_sha(self, branch: str) -> str | None:
        got = self._client.get(f"/repos/{self._repo}/git/ref/heads/{self._ref(branch)}")
        if got.status_code == 404:
            return None
        got.raise_for_status()
        sha = (got.json().get("object") or {}).get("sha")
        return sha if isinstance(sha, str) and sha else None

    def get_pull_request(self, number: int) -> dict[str, Any] | None:
        if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
            raise ValueError("not a pull request number")
        got = self._client.get(f"/repos/{self._repo}/pulls/{number}")
        if got.status_code == 404:
            return None
        got.raise_for_status()
        body = got.json()
        return body if isinstance(body, dict) else None

    def create_pull_request(self, head: str, base: str, title: str, body: str) -> str:
        """Open a pull request from ``head`` (a ``responder/<fp>`` branch) into ``base`` and return its
        URL (#260: the runner opens it, not the agent). VERIFY: ``POST /repos/{repo}/pulls`` with
        ``title``, ``head``, ``base``, ``body`` answers 201 with ``html_url``."""
        checked_branch(head)
        made = self._client.post(f"/repos/{self._repo}/pulls",
                                 json={"title": title, "head": head, "base": base, "body": body})
        made.raise_for_status()
        url = made.json().get("html_url")
        if not isinstance(url, str) or not url:
            raise ValueError("no pull request URL in the reply")
        return url

    def delete_branch_if_exists(self, branch: str) -> bool:
        ref = self._ref(branch)
        got = self._client.get(f"/repos/{self._repo}/git/ref/heads/{ref}")
        if got.status_code == 404:
            return False
        got.raise_for_status()
        self._client.delete(f"/repos/{self._repo}/git/refs/heads/{ref}").raise_for_status()
        return True
