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

    def __init__(self, existing: set[str] | None = None, *, pulls: dict[int, dict[str, Any]] | None = None,
                 repo: str = "owner/repo") -> None:
        self.branches: dict[str, str] = {b: "sha-0" for b in (existing or ())}  # branch -> head SHA
        self.pulls: dict[int, dict[str, Any]] = dict(pulls or {})
        self.deleted: list[str] = []
        self.created: list[dict[str, str]] = []  # pull requests the RUNNER opened (#260)
        self.fail_create = False
        self._repo = repo
        self._pushes = 0

    def create_pull_request(self, head: str, base: str, title: str, body: str) -> str:
        if self.fail_create:
            raise RuntimeError("422")
        number = 100 + len(self.created)
        self.created.append({"head": head, "base": base, "title": title, "body": body})
        self.pulls[number] = {"number": number, "state": "open",
                              "head": {"ref": head, "repo": {"full_name": self._repo}}}
        return f"https://github.com/{self._repo}/pull/{number}"

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
