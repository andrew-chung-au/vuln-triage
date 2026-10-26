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

    def __init__(self, existing: set[str] | None = None) -> None:
        self.branches: set[str] = set(existing or ())
        self.deleted: list[str] = []

    def delete_branch_if_exists(self, branch: str) -> bool:
        if branch in self.branches:
            self.branches.discard(branch)
            self.deleted.append(branch)
            return True
        return False


class FakeGitHub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def open_pull_request(self, branch: str, title: str, body: str) -> str:
        self.calls.append(("open_pull_request", {"branch": branch, "title": title, "body": body}))
        return f"fake://pull/{branch}"
