#!/usr/bin/env python3
"""P-FLAG-GONE: fail a production promotion while a test-only switch is present.

Usage: python3 ci/check_flag_gone.py [TREE]    (TREE defaults to ".")

Exit status: 0 = clean (P-FLAG-GONE passes), 1 = a rule failed, 2 = bad usage.

Runs ONLY in the production-promotion workflow (``deploy-prod`` in
``.github/workflows/deploy.yml``), against the tree of the commit being
promoted. It is not part of ``make test-compose`` or any pull-request job, so
the pull-request gate stays green while the demo defect still exists. Its own
correctness is tested under ``make test`` (``tests/test_flag_gone.py``) against
two fixture trees, one that must fail and one that must pass.

Two rules (issue #161, task 29; re-scoped from #172 by the owner on 2026-10-26):

1. demo-defect. The demo defect (``VT_DEMO_DEFECT=notify_no_fix``, task 28a) must
   not exist anywhere in the code. Any tracked non-documentation file, or file
   name, that mentions ``VT_DEMO_DEFECT``, any ``demo_defect`` / ``DemoDefect``
   identifier, or the ``notify_no_fix`` token fails the rule. ``notify_no_fixed_
   version`` (a different name) does not match.

2. fixtures-flag. ``backend/vulntriage/ingest/feeds.py`` ships in every image by
   design, so this rule does NOT look for the module. It checks the flag/value
   and its fail-closed refusal gate (``require_feeds_allowed``):
     a. no production artifact (``compose.yaml``, ``.env.example``, any
        ``Dockerfile*``, anything under ``terraform/``) sets ``VT_FEEDS`` to
        ``fixtures`` on a non-comment line; and
     b. the gate still exists: ``require_feeds_allowed`` is defined in
        ``backend/vulntriage/ingest/settings.py`` and called at start-up in
        ``backend/vulntriage/main.py``.

VERIFY: the wording of rule 2 (flag/value and gate, not module existence) is the
owner's decision in #229; change this file only after that decision.

Documentation and records (``*.md``, ``_docs/``, ``_session-summaries/``) are
not code and are not scanned, nor are build output and dependency folders. The
check and its own test mention the strings by necessity and are skipped by path.
Standard library only.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".scratch",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".terraform",
}
# Documentation and records at the top of the tree (not code).
DOC_TOP_DIRS = {"_docs", "_session-summaries"}
DOC_SUFFIXES = {".md"}
# The check and its test name the strings by necessity.
SELF_PATHS = {"ci/check_flag_gone.py", "tests/test_flag_gone.py"}
MAX_BYTES = 2_000_000

DEMO_DEFECT = re.compile(
    r"demo_?defect|(?<![a-z0-9])notify_no_fix(?![a-z0-9])",
    re.IGNORECASE,
)

FIXTURES_SET = re.compile(r"VT_FEEDS[\"']?\s*[=:]\s*[\"']?fixtures\b", re.IGNORECASE)
GATE_DEFINITION = ("backend/vulntriage/ingest/settings.py", re.compile(r"^\s*def\s+require_feeds_allowed\b"))
GATE_CALL = ("backend/vulntriage/main.py", re.compile(r"^[^#\n]*\brequire_feeds_allowed\("))


def _is_production_artifact(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return rel in {"compose.yaml", ".env.example"} or name.startswith("Dockerfile") or rel.startswith("terraform/")


def _is_comment(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("#") or stripped.startswith("//")


def _walk(root: Path):
    """Yield (relative posix path, absolute path) for every code file under root."""
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        if rel_dir == ".":
            dirnames[:] = [d for d in dirnames if d not in DOC_TOP_DIRS]
        for filename in sorted(filenames):
            absolute = Path(dirpath) / filename
            rel = filename if rel_dir == "." else f"{rel_dir}/{filename}"
            if rel in SELF_PATHS or absolute.suffix.lower() in DOC_SUFFIXES:
                continue
            if absolute.is_symlink():
                continue
            yield rel, absolute


def _read_lines(path: Path) -> list[str] | None:
    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        return path.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return None  # binary or unreadable: not code we can scan


def check(root: Path) -> list[str]:
    """Return the findings for the tree at root (empty = P-FLAG-GONE passes)."""
    findings: list[str] = []
    for rel, absolute in _walk(root):
        if DEMO_DEFECT.search(rel):
            findings.append(f"demo-defect: file name {rel}")
        lines = _read_lines(absolute)
        if lines is None:
            continue
        production = _is_production_artifact(rel)
        for number, line in enumerate(lines, start=1):
            if DEMO_DEFECT.search(line):
                findings.append(f"demo-defect: {rel}:{number}: {line.strip()[:120]}")
            if production and not _is_comment(line) and FIXTURES_SET.search(line):
                findings.append(f"fixtures-flag: {rel}:{number}: sets VT_FEEDS to fixtures in a production artifact")
    for rel, pattern in (GATE_DEFINITION, GATE_CALL):
        lines = _read_lines(root / rel)
        if lines is None or not any(pattern.search(line) for line in lines):
            what = "defined" if pattern is GATE_DEFINITION[1] else "called"
            findings.append(f"fixtures-flag: require_feeds_allowed is not {what} in {rel} (the fail-closed gate is missing)")
    return findings


def main(argv: list[str]) -> int:
    if len(argv) > 2 or (len(argv) == 2 and argv[1] in {"-h", "--help"}):
        print(__doc__)
        return 2
    root = Path(argv[1] if len(argv) == 2 else ".")
    if not root.is_dir():
        print(f"P-FLAG-GONE: {root} is not a directory", file=sys.stderr)
        return 2
    findings = check(root)
    for finding in findings:
        print(finding)
    if findings:
        print(f"P-FLAG-GONE: FAIL ({len(findings)} finding(s)); the production promotion must stop")
        return 1
    print("P-FLAG-GONE: PASS (no demo defect, no fixtures flag in a production artifact, gate present)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
