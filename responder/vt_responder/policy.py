"""Tool and path allowlist for the real runner (task 28d / #221).

Pure functions, no SDK import: the SDK permission callback and the PreToolUse
hook in ``sdk_session`` both call ``ToolPolicy.check`` and nothing else decides.
Anything not explicitly allowed is denied.

Allowed: read anything inside the checkout (except ``.env*`` files other than
``.env.example``), edit code and tests inside the checkout's writable roots,
run the project's test targets, commit, push ``responder/<fingerprint>`` and
open a pull request for it.

Denied (each has its own reason code and test): a write to ``.github/``, to
Terraform or other infrastructure paths, to an ``.env*`` file; any path outside
the checkout (``..`` traversal and symlink escape included); a push to any
branch other than ``responder/<fingerprint>``; a push to ``main``; any merge.

Fingerprints and finding ids are never passed to git or gh as a bare argument:
the branch is always built as ``responder/<fingerprint>`` and the fingerprint
must fully match ``[A-Za-z0-9_-]{1,64}``. A fingerprint such as ``-x`` is
therefore only ever seen as ``responder/-x``.
"""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SAFE_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
BRANCH_PREFIX = "responder/"

# Top-level directories the agent may edit: code and tests only.
WRITABLE_ROOTS = frozenset({"backend", "tests", "frontend", "responder"})
# A path with any of these components is never writable (CI config, infra, hooks).
PROTECTED_COMPONENTS = frozenset(
    {".git", ".github", "terraform", ".terraform", "deploy", "ci", "observability",
     "infra", "infrastructure", ".devcontainer", ".claude", ".opencode", "agent-kit"}
)
PROTECTED_SUFFIXES = (".tf", ".tfvars", ".tfstate", ".tfplan")

# The CLI runtime (#260): the runner's diff gate also refuses these, and the generated CLI
# deny rules (cli_rules.py) are built from the same constants. Lockfiles change only by an
# install the runner controls; the responder's own code is what bounds the agent.
PROTECTED_LOCKFILES = frozenset(
    {"package-lock.json", "npm-shrinkwrap.json", "uv.lock", "poetry.lock", "yarn.lock", "pnpm-lock.yaml"}
)
PROTECTED_PATH_PREFIXES = ("responder/vt_responder/",)
# Git subcommands the CLI agent may run (it commits locally; the runner pushes).
CLI_GIT_READ = ("status", "diff", "log")
CLI_GIT_WRITE = ("add", "commit")

READ_TOOLS = frozenset({"Read", "Glob", "Grep"})
WRITE_TOOLS = frozenset({"Edit", "Write", "MultiEdit"})
KNOWN_TOOLS = READ_TOOLS | WRITE_TOOLS | {"Bash"}
MAKE_TARGETS = frozenset({"backend-test", "responder-test", "test"})

_SHELL_META = re.compile(r"[;&|<>$`(){}\\\n\r]")
_READ_FLAGS = frozenset({"--stat", "--short", "-s", "--oneline", "--name-only", "--cached", "--staged"})


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str  # a short machine code; safe to log

    @staticmethod
    def ok() -> "Decision":
        return Decision(True, "allowed")

    @staticmethod
    def deny(reason: str) -> "Decision":
        return Decision(False, reason)


def _is_env_file(name: str, *, allow_example: bool = True) -> bool:
    """An ``.env*`` file, matched case-insensitively. ``.env.example`` is readable."""
    lowered = name.lower()
    if allow_example and lowered == ".env.example":
        return False
    return lowered.startswith(".env")


def _is_protected_name(name: str) -> bool:
    lowered = name.lower()
    return (
        _is_env_file(name, allow_example=False)
        or lowered.endswith(PROTECTED_SUFFIXES)
        or lowered.startswith("dockerfile")
        or (lowered.startswith("compose") and lowered.endswith((".yaml", ".yml")))
    )


def resolve_in_checkout(checkout: Path, raw: str) -> Path | None:
    """The real path of ``raw`` if it is inside ``checkout``, else None.

    Relative paths are taken from the checkout. ``realpath`` follows symlinks,
    so a link that points outside is refused, and ``..`` is collapsed first.
    """
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        return None
    root = Path(os.path.realpath(checkout))
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    real = Path(os.path.realpath(candidate))
    try:
        real.relative_to(root)
    except ValueError:
        return None
    return real


class ToolPolicy:
    def __init__(self, checkout: Path, fingerprint: str) -> None:
        if not SAFE_ID.fullmatch(fingerprint):
            raise ValueError("unsafe fingerprint")
        self._root = Path(os.path.realpath(checkout))
        self.branch = BRANCH_PREFIX + fingerprint

    # -- paths -----------------------------------------------------------
    def check_read_path(self, raw: str) -> Decision:
        real = resolve_in_checkout(self._root, raw)
        if real is None:
            return Decision.deny("path_outside_checkout")
        if _is_env_file(real.name):
            return Decision.deny("env_file")
        return Decision.ok()

    def check_write_path(self, raw: str) -> Decision:
        real = resolve_in_checkout(self._root, raw)
        if real is None:
            return Decision.deny("path_outside_checkout")
        return self._check_write_parts(real.relative_to(self._root).parts)

    def _check_write_parts(self, parts: tuple[str, ...]) -> Decision:
        """The write rules for a path already split relative to the checkout (no filesystem access)."""
        if not parts:
            return Decision.deny("path_not_allowed")
        lowered_parts = tuple(p.lower() for p in parts)
        if _is_env_file(parts[-1], allow_example=False):
            return Decision.deny("env_file")
        if ".github" in lowered_parts:
            return Decision.deny("github_dir")
        if PROTECTED_COMPONENTS.intersection(lowered_parts) or _is_protected_name(parts[-1]):
            return Decision.deny("infrastructure_path")
        if parts[0] not in WRITABLE_ROOTS:
            return Decision.deny("path_not_allowed")
        return Decision.ok()

    def check_publish_path(self, raw: str) -> Decision:
        """The runner-side gate for a path an agent commit changed (#260): the write rules
        plus lockfiles and the responder's own code.

        ``raw`` is the path string a commit contains, judged LEXICALLY: no ``realpath``, no filesystem
        access. A working tree that was changed after the commit (a directory swapped for a symlink)
        therefore cannot change the verdict. Absolute paths, ``..``, ``.`` and empty components are refused."""
        if not isinstance(raw, str) or not raw or "\x00" in raw:
            return Decision.deny("path_outside_checkout")
        parts = tuple(raw.split("/"))
        if raw.startswith("/") or any(p in ("", ".", "..") for p in parts):
            return Decision.deny("path_outside_checkout")
        decision = self._check_write_parts(parts)
        if not decision.allowed:
            return decision
        if parts[-1].lower() in PROTECTED_LOCKFILES:
            return Decision.deny("lockfile")
        rel = "/".join(parts)
        if any((rel.lower() + "/").startswith(prefix) for prefix in PROTECTED_PATH_PREFIXES):
            return Decision.deny("guard_module")
        return Decision.ok()

    # -- tools -----------------------------------------------------------
    def check(self, tool_name: str, tool_input: dict[str, Any] | None) -> Decision:
        tool_input = tool_input if isinstance(tool_input, dict) else {}
        if "merge" in str(tool_name).lower():
            return Decision.deny("merge_denied")
        if tool_name in WRITE_TOOLS:
            return self.check_write_path(tool_input.get("file_path", ""))
        if tool_name in READ_TOOLS:
            # Glob and Grep may omit the path (they then search the checkout).
            raw = tool_input.get("file_path") or tool_input.get("path")
            return self.check_read_path(raw) if raw else Decision.ok()
        if tool_name == "Bash":
            return self.check_command(str(tool_input.get("command", "")))
        return Decision.deny("tool_not_allowed")

    def check_command(self, command: str) -> Decision:
        if "merge" in command.lower():
            return Decision.deny("merge_denied")
        if _SHELL_META.search(command):
            return Decision.deny("shell_metacharacter")
        try:
            argv = shlex.split(command)
        except ValueError:
            return Decision.deny("command_not_allowed")
        if not argv:
            return Decision.deny("command_not_allowed")
        head, rest = argv[0], argv[1:]
        if head == "make":
            ok = len(rest) == 1 and rest[0] in MAKE_TARGETS
            return Decision.ok() if ok else Decision.deny("command_not_allowed")
        if head == "git":
            return self._check_git(rest)
        if head == "gh":
            return self._check_gh(rest)
        return Decision.deny("command_not_allowed")

    def _check_git(self, args: list[str]) -> Decision:
        if not args:
            return Decision.deny("command_not_allowed")
        sub, rest = args[0], args[1:]
        if sub in ("status", "diff", "log"):
            for a in rest:
                if a.startswith("-"):
                    if a not in _READ_FLAGS:
                        return Decision.deny("command_not_allowed")
                else:
                    d = self.check_read_path(a)
                    if not d.allowed:
                        return d
            return Decision.ok()
        if sub == "add":
            paths = rest[1:] if rest[:1] == ["--"] else rest
            if not paths or any(p.startswith("-") for p in paths):
                return Decision.deny("command_not_allowed")
            for p in paths:
                d = self.check_write_path(p)
                if not d.allowed:
                    return d
            return Decision.ok()
        if sub == "commit":
            ok = len(rest) == 2 and rest[0] == "-m" and bool(rest[1]) and not rest[1].startswith("-")
            return Decision.ok() if ok else Decision.deny("command_not_allowed")
        if sub in ("checkout", "switch"):
            flag = "-b" if sub == "checkout" else "-c"
            if len(rest) == 2 and rest[0] == flag and rest[1] == self.branch:
                return Decision.ok()
            return Decision.deny("branch_not_allowed")
        if sub == "push":
            return self._check_push(rest)
        return Decision.deny("command_not_allowed")

    def _check_push(self, rest: list[str]) -> Decision:
        args = list(rest)
        if args and args[0] in ("-u", "--set-upstream"):
            args = args[1:]
        if len(args) != 2 or args[0] != "origin":
            # Flags (--force, --delete, --all, --mirror, ...) and bare pushes land here.
            return Decision.deny("push_not_allowed")
        ref = args[1]
        if ref == self.branch:
            return Decision.ok()
        targets = {ref, ref.rsplit(":", 1)[-1]}
        if any(t.removeprefix("refs/heads/") in ("main", "master") for t in targets):
            return Decision.deny("push_main")
        return Decision.deny("push_other_branch")

    def _check_gh(self, args: list[str]) -> Decision:
        if args[:2] != ["pr", "create"]:
            return Decision.deny("command_not_allowed")
        rest = args[2:]
        i = 0
        while i < len(rest):
            flag = rest[i]
            if flag == "--draft":
                i += 1
                continue
            if flag in ("--title", "--body", "--head", "--base") and i + 1 < len(rest):
                value = rest[i + 1]
                if flag == "--head" and value != self.branch:
                    return Decision.deny("push_other_branch")
                if flag == "--base" and value != "main":
                    return Decision.deny("command_not_allowed")
                i += 2
                continue
            return Decision.deny("command_not_allowed")
        return Decision.ok()
