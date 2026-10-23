"""Record GitHub fixtures from public repositories (run by the human, never by tests).

Usage (through make): ``make record-fixtures SOURCE=github``. Not collected by
pytest and not called by ``make test``, ``make verify`` or CI.

Reads the confirmed repositories (``owner/repo``, one per line) from
``tests/fixtures/github/repositories.txt``, calls the live GitHub API with NO
token (public repositories only), writes ``<owner>__<repo>/repo.json``,
``commit.txt`` and ``contents/<path>`` under ``tests/fixtures/github/``, and
prints the MANIFEST rows to paste into ``tests/fixtures/MANIFEST.md``. Check
the recorded files for tokens and private data before committing them.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))

from vulntriage.ingest.github import GitHubReader, split_repository_url  # noqa: E402
from vulntriage.ingest.requirements import parse_requirements, resolve_include  # noqa: E402

SOURCES = ("github", "osv", "kev", "epss")
GITHUB_DIR = HERE / "fixtures" / "github"
REPOSITORIES = GITHUB_DIR / "repositories.txt"
ROOT_FILES = ("uv.lock", "requirements.txt", "package-lock.json")
MAX_INCLUDES = 20


def read_repositories() -> list[tuple[str, str]]:
    repos: list[tuple[str, str]] = []
    if not REPOSITORIES.is_file():
        return repos
    for line in REPOSITORIES.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parsed = split_repository_url(f"https://github.com/{line}")
        if parsed is None:
            raise SystemExit(f"repositories.txt: not an owner/repo: {line!r}")
        repos.append(parsed)
    return repos


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def record_github() -> int:
    repos = read_repositories()
    if not repos:
        print(f"no repositories confirmed in {REPOSITORIES}; add owner/repo lines first", file=sys.stderr)
        return 2
    reader = GitHubReader(token_provider=lambda: None)
    today = dt.date.today().isoformat()
    print("| path | fixture | source URL | capture date | GitHub commit SHA | capture method | token/private-data check |")
    for owner, repo in repos:
        folder = GITHUB_DIR / f"{owner}__{repo}"
        info = reader.get_repository(owner, repo)
        sha = reader.resolve_commit(owner, repo)
        if sha is None:
            print(f"{owner}/{repo} is empty; skipped", file=sys.stderr)
            continue
        write(folder / "repo.json", json.dumps(info, indent=2) + "\n")
        write(folder / "commit.txt", sha + "\n")
        recorded = ["repo.json", "commit.txt"]
        queue = list(ROOT_FILES)
        seen: set[str] = set()
        while queue and len(seen) < MAX_INCLUDES + 2:
            name = queue.pop(0)
            if name in seen:
                continue
            seen.add(name)
            text = reader.read_file(owner, repo, sha, name)
            if text is None:
                continue
            write(folder / "contents" / name, text)
            recorded.append(f"contents/{name}")
            if name.endswith(".txt"):
                for include in parse_requirements(text, name).includes:
                    target = resolve_include(name, include.target)
                    if target:
                        queue.append(target)
        for item in recorded:
            url = f"https://github.com/{owner}/{repo}"
            print(
                f"| tests/fixtures/github/{owner}__{repo}/{item} | {item} | {url} | {today} | {sha} "
                "| make record-fixtures SOURCE=github | TO CHECK by the Engineer |"
            )
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in (*SOURCES, "all"):
        print("usage: record_fixtures.py <github|osv|kev|epss|all>", file=sys.stderr)
        return 2
    source = argv[1]
    if source in ("osv", "kev", "epss"):
        print(f"{source}: implemented in task 5/6", file=sys.stderr)
        return 2
    return record_github()  # "github", or "all" (only github exists so far)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
