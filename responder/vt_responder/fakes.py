"""In-process fake git and GitHub clients for stub mode.

They only record calls. Nothing here touches a repository, a network or a
token. The false-positive path must never call either (asserted in tests);
the defect path calls the fake git for branch and commit but never ``push``.
"""

from __future__ import annotations

from typing import Any


class FakeGit:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def create_branch(self, name: str) -> None:
        self.calls.append(("create_branch", {"name": name}))

    def commit(self, branch: str, files: list[str], message: str) -> None:
        self.calls.append(("commit", {"branch": branch, "files": list(files), "message": message}))

    def push(self, branch: str) -> None:  # pragma: no cover - must never run in stub mode
        self.calls.append(("push", {"branch": branch}))


class FakeBranchClient:
    """Real-mode fake: records branches the 'agent' pushed and their deletion; no network."""

    def __init__(self, existing: set[str] | None = None, *, pulls: dict[int, dict[str, Any]] | None = None) -> None:
        self.branches: dict[str, str] = {b: "sha-0" for b in (existing or ())}  # branch -> head SHA
        self.pulls: dict[int, dict[str, Any]] = dict(pulls or {})
        self.deleted: list[str] = []
        self._pushes = 0

    def push(self, branch: str) -> None:
        """What the agent's ``git push`` does: create the branch or move its head."""
        self._pushes += 1
        self.branches[branch] = f"sha-{self._pushes}"

    def get_branch_sha(self, branch: str) -> str | None:
        return self.branches.get(branch)

    def get_pull_request(self, number: int) -> dict[str, Any] | None:
        return self.pulls.get(number)

    def delete_branch_if_exists(self, branch: str) -> bool:
        if branch in self.branches:
            del self.branches[branch]
            self.deleted.append(branch)
            return True
        return False


class FakeGitHub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def open_pull_request(self, branch: str, title: str, body: str) -> str:
        self.calls.append(("open_pull_request", {"branch": branch, "title": title, "body": body}))
        return f"fake://pull/{branch}"
