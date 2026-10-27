"""The runner's diff gate, push and pull request for the CLI runtime (#260).

The agent only commits locally. After the run (and after its processes are killed) this module,
independent of what the CLI enforced, decides whether the commits may leave the machine:

* the new head must descend from the commit that was cloned (``base``), with no merge commit and at
  most ``max_commits`` commits;
* every changed file is added, modified or deleted as a regular file (no symlink, no submodule, no
  type change, no new executable, no mode change) and passes ``ToolPolicy.check_publish_path``: inside
  the writable roots, not ``.github/``, infrastructure, ``.env*``, Terraform, a lockfile, or the
  responder's own code;
* ``.git/config`` is byte-identical to what it was right after the clone (code the agent runs could
  otherwise point the push, with the token, somewhere else); hooks and the fsmonitor setting are
  switched off for the runner's own git calls.

Only then does the runner push ``<head sha>:refs/heads/responder/<fingerprint>`` (no force; the token
reaches this one git call only, through ``git_auth_env``) and open the pull request through the
REST client, with a title and body the runner composes. Any refusal raises ``PublishError`` with a
short code; the runner treats it as a failed run (kill, remove the checkout, clean the branch).

The agent's summary, the only agent text in the body, is redacted, cut short, stripped of backticks
and put in a code block (a code block does not notify an ``@name``).
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from .checkout import git_auth_env
from .config import DEFAULT_MAX_COMMITS
from .envscrub import minimal_env, redact
from .policy import BRANCH_PREFIX, ToolPolicy

MAX_FILES = 40
MAX_SUMMARY_CHARS = 300
BASE_BRANCH = "main"
_SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
REGULAR_MODES = ("100644", "100755")
_IDENTITY = {
    "GIT_AUTHOR_NAME": "VulnTriage responder", "GIT_COMMITTER_NAME": "VulnTriage responder",
    "GIT_AUTHOR_EMAIL": "responder@users.noreply.github.com",
    "GIT_COMMITTER_EMAIL": "responder@users.noreply.github.com",
}


class PublishError(RuntimeError):
    """The commits may not be published. ``reason`` is a short machine code, safe to log."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Change:
    status: str  # A, M, D, T, ... (``git diff --raw --no-renames``)
    old_mode: str
    new_mode: str
    path: str


@dataclass(frozen=True)
class Snapshot:
    base: str  # the commit that was cloned
    config: str  # digest of .git/config at that moment


class PublishGit(Protocol):
    def head(self, checkout: Path) -> str: ...
    def config_digest(self, checkout: Path) -> str: ...
    def is_ancestor(self, checkout: Path, base: str, head: str) -> bool: ...
    def commit_count(self, checkout: Path, base: str, head: str) -> int: ...
    def merge_count(self, checkout: Path, base: str, head: str) -> int: ...
    def changes(self, checkout: Path, base: str, head: str) -> list[Change]: ...
    def squash(self, checkout: Path, base: str, head: str, message: str) -> str: ...
    def push(self, checkout: Path, sha: str, branch: str) -> None: ...


class PullRequestClient(Protocol):
    def create_pull_request(self, head: str, base: str, title: str, body: str) -> str: ...


def check_changes(checkout: Path, fingerprint: str, changes: Iterable[Change]) -> list[str]:
    """The paths if every change may be published, else ``PublishError``. Pure apart from path resolution."""
    policy = ToolPolicy(checkout, fingerprint)
    paths: list[str] = []
    for change in changes:
        if any(ord(c) < 32 or c == "\x7f" for c in change.path):
            raise PublishError("diff_path_odd_name")
        if change.status not in ("A", "M", "D"):
            raise PublishError("diff_type_change" if change.status == "T" else "diff_status_unexpected")
        if "120000" in (change.old_mode, change.new_mode):
            raise PublishError("diff_symlink")
        if "160000" in (change.old_mode, change.new_mode):
            raise PublishError("diff_submodule")
        if change.status == "A" and change.new_mode != "100644":
            raise PublishError("diff_mode_unexpected")  # a new file must be a plain, non-executable file
        if change.status == "M" and (change.old_mode != change.new_mode or change.new_mode not in REGULAR_MODES):
            raise PublishError("diff_mode_changed")
        if change.status == "D" and change.old_mode not in REGULAR_MODES:
            raise PublishError("diff_mode_unexpected")
        decision = policy.check_publish_path(change.path)
        if not decision.allowed:
            raise PublishError(f"diff_path_{decision.reason}")
        paths.append(change.path)
    if not paths:
        raise PublishError("diff_empty")
    if len(paths) > MAX_FILES:
        raise PublishError("diff_too_many_files")
    return paths


def compose_pull_request(fingerprint: str, finding_id: str | None, files: list[str], summary: str | None,
                         secrets: Iterable[str]) -> tuple[str, str]:
    """Title and body, composed by the runner from validated identifiers and the checked file list."""
    title = f"Fix undelivered notification for alert {fingerprint}"
    lines = [
        f"Proposed by the VulnTriage responder for alert `{fingerprint}`"
        + (f" (finding `{finding_id}`)." if finding_id else "."),
        "",
        "The responder checked the agent's commits before pushing: only code and tests under the writable "
        "roots changed, with no workflow, infrastructure, lockfile, `.env` or responder-code file touched. "
        "A person reviews and merges; the responder never merges.",
        "",
        "Changed files:",
        *[f"- `{path}`" for path in files],
    ]
    text = redact(summary or "", list(secrets)) or ""
    text = re.sub(r"\s+", " ", text.replace("`", "'")).strip()[:MAX_SUMMARY_CHARS]
    if text:
        lines += ["", "Agent summary (untrusted text, redacted and shortened):", "```", text, "```"]
    return title, "\n".join(lines)


class GitPublisher:
    def __init__(self, git: PublishGit, pulls: PullRequestClient, *, secrets: Iterable[str] = (),
                 max_commits: int = DEFAULT_MAX_COMMITS) -> None:
        self._git = git
        self._pulls = pulls
        self._secrets = tuple(s for s in secrets if s)
        self._max_commits = max_commits

    def snapshot(self, checkout: Path) -> Snapshot:
        """Called after the clone and install, before the agent starts."""
        return Snapshot(self._git.head(checkout), self._git.config_digest(checkout))

    def publish(self, checkout: Path, snapshot: Snapshot, fingerprint: str, finding_id: str | None,
                summary: str | None) -> str:
        git = self._git
        try:
            if git.config_digest(checkout) != snapshot.config:
                raise PublishError("git_config_modified")
            head = git.head(checkout)
            if head == snapshot.base:
                raise PublishError("no_commits")
            if not git.is_ancestor(checkout, snapshot.base, head):
                raise PublishError("base_not_cloned_head")
            if git.merge_count(checkout, snapshot.base, head) > 0:
                raise PublishError("merge_commit")
            if git.commit_count(checkout, snapshot.base, head) > self._max_commits:
                raise PublishError("too_many_commits")
            files = check_changes(checkout, fingerprint, git.changes(checkout, snapshot.base, head))
        except PublishError:
            raise
        except Exception:  # noqa: BLE001 - a git failure while checking is a refusal, never a push
            raise PublishError("diff_check_failed") from None
        branch = BRANCH_PREFIX + fingerprint
        title, body = compose_pull_request(fingerprint, finding_id, files, summary, self._secrets)
        try:
            # ONE commit, built by the runner on the cloned base from the tree the gate checked: the agent's own
            # commits (and anything added then removed in them) are never pushed, and the message is ours.
            squashed = git.squash(checkout, snapshot.base, head, title)
            git.push(checkout, squashed, branch)
        except Exception:  # noqa: BLE001 - git's stderr may echo a URL; not carried
            raise PublishError("push_failed") from None
        try:
            return self._pulls.create_pull_request(branch, BASE_BRANCH, title, body)
        except Exception:  # noqa: BLE001
            raise PublishError("pull_request_create_failed") from None


class SubprocessPublishGit:
    """The real git seam; not exercised by tests (they pass a fake). The token reaches ``push`` only."""

    def __init__(self, repo: str, token: str) -> None:
        self._url = f"https://github.com/{repo}.git"
        self._token = token

    def _git(self, checkout: Path, args: list[str], *, with_token: bool = False, ok: tuple[int, ...] = (0,),
             extra_env: dict[str, str] | None = None):
        env = minimal_env(os.environ)
        env.update(extra_env or {})
        # The agent runs with the owner's real HOME and could have written ~/.gitconfig (a url.insteadOf,
        # http.proxy, http.sslVerify=false ...): neither the global nor the system config is read here.
        # Everything this module needs is passed with -c below or by git_auth_env.
        env.update({"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
        if with_token:
            env.update(git_auth_env(self._token))
        # Code the agent ran could have planted a hook or an fsmonitor command in .git/config:
        # both are switched off for every call the runner makes here.
        # --no-replace-objects: a refs/replace/* ref the agent made must not change what the gate reads.
        argv = ["git", "--no-replace-objects", "-c", f"core.hooksPath={os.devnull}", "-c", "core.fsmonitor=false",
                *args]
        done = subprocess.run(argv, cwd=checkout, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=300, check=False)
        if done.returncode not in ok:
            raise RuntimeError(f"git {args[0]} failed")  # stderr not included
        return done

    def head(self, checkout: Path) -> str:
        sha = self._git(checkout, ["rev-parse", "HEAD"]).stdout.strip()
        if not _SHA.fullmatch(sha):
            raise RuntimeError("unexpected head")
        return sha

    def config_digest(self, checkout: Path) -> str:
        return hashlib.sha256((checkout / ".git" / "config").read_bytes()).hexdigest()

    def is_ancestor(self, checkout: Path, base: str, head: str) -> bool:
        return self._git(checkout, ["merge-base", "--is-ancestor", base, head], ok=(0, 1)).returncode == 0

    def commit_count(self, checkout: Path, base: str, head: str) -> int:
        return int(self._git(checkout, ["rev-list", "--count", f"{base}..{head}"]).stdout.strip())

    def merge_count(self, checkout: Path, base: str, head: str) -> int:
        return int(self._git(checkout, ["rev-list", "--count", "--merges", f"{base}..{head}"]).stdout.strip())

    def changes(self, checkout: Path, base: str, head: str) -> list[Change]:
        out = self._git(checkout, ["diff", "--raw", "--no-renames", "--no-ext-diff", "--no-textconv", "-z",
                                   base, head]).stdout
        tokens = out.split("\0")
        found: list[Change] = []
        i = 0
        while i + 1 < len(tokens) and tokens[i].startswith(":"):
            old_mode, new_mode, _old, _new, status = tokens[i][1:].split(" ")
            found.append(Change(status[:1], old_mode, new_mode, tokens[i + 1]))
            i += 2
        return found

    def squash(self, checkout: Path, base: str, head: str, message: str) -> str:
        """One new commit: ``head``'s tree, parent ``base``, the runner's identity and message."""
        if not _SHA.fullmatch(base) or not _SHA.fullmatch(head):
            raise RuntimeError("refused")
        tree = self._git(checkout, ["rev-parse", f"{head}^{{tree}}"]).stdout.strip()
        if not _SHA.fullmatch(tree):
            raise RuntimeError("unexpected tree")
        sha = self._git(checkout, ["commit-tree", tree, "-p", base, "-m", message], extra_env=_IDENTITY).stdout.strip()
        if not _SHA.fullmatch(sha):
            raise RuntimeError("unexpected commit")
        return sha

    def push(self, checkout: Path, sha: str, branch: str) -> None:
        if not _SHA.fullmatch(sha) or not branch.startswith(BRANCH_PREFIX):
            raise RuntimeError("refused")
        # An explicit URL and a sha refspec: no remote name from .git/config, no force.
        self._git(checkout, ["push", "--", self._url, f"{sha}:refs/heads/{branch}"], with_token=True)
