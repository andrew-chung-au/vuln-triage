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
from vulntriage.ingest.osv import OsvClient, Query  # noqa: E402
from vulntriage.ingest.requirements import parse_requirements, resolve_include  # noqa: E402
from vulntriage.ingest.signals import EpssClient, KevClient  # noqa: E402

SOURCES = ("github", "osv", "kev", "epss")
GITHUB_DIR = HERE / "fixtures" / "github"
OSV_DIR = HERE / "fixtures" / "osv"
KEV_DIR = HERE / "fixtures" / "kev"
EPSS_DIR = HERE / "fixtures" / "epss"
REPOSITORIES = GITHUB_DIR / "repositories.txt"
OSV_PACKAGES = OSV_DIR / "packages.txt"
SIGNAL_CVES = HERE / "fixtures" / "cves.txt"
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


def read_osv_packages() -> list[Query]:
    """Confirmed ``ecosystem name version`` lines from ``fixtures/osv/packages.txt``."""
    queries: list[Query] = []
    if not OSV_PACKAGES.is_file():
        return queries
    for line in OSV_PACKAGES.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 3:
            raise SystemExit(f"packages.txt: expected 'ecosystem name version', got {line!r}")
        queries.append(Query(parts[0], parts[1], parts[2]))
    return queries


def record_osv() -> int:
    """Capture OSV querybatch and vuln-detail fixtures for the confirmed packages.

    Public OSV API, no key. Writes ``querybatch.json`` (a ``by_query`` map the
    stub replays) and ``vulns/<id>.json`` for every advisory the queries return.
    Hand-written fixtures already in the directory are left in place; only the
    files for the confirmed packages are rewritten.
    """
    queries = read_osv_packages()
    if not queries:
        print(
            f"no packages confirmed in {OSV_PACKAGES}; add 'ecosystem name version' lines first",
            file=sys.stderr,
        )
        return 2
    client = OsvClient()
    today = dt.date.today().isoformat()
    batch = client.query_batch(queries)

    by_query: dict[str, dict[str, object]] = {}
    vuln_ids: set[str] = set()
    for query, refs in zip(queries, batch):
        key = f"{query.ecosystem}|{query.name}|{query.version}"
        by_query[key] = {
            "vulns": [
                {"id": ref.osv_id, "modified": ref.modified} for ref in refs
            ]
        }
        vuln_ids.update(ref.osv_id for ref in refs)

    write(OSV_DIR / "querybatch.json", json.dumps({"by_query": by_query}, indent=2) + "\n")
    print("| path | fixture | source URL | capture date | commit SHA | capture method | check |")
    print(
        f"| tests/fixtures/osv/querybatch.json | querybatch map | https://api.osv.dev/v1/querybatch "
        f"| {today} | n/a | make record-fixtures SOURCE=osv | TO CHECK by the Engineer |"
    )
    for osv_id in sorted(vuln_ids):
        advisory = client.get_vuln(osv_id)
        write(OSV_DIR / "vulns" / f"{osv_id}.json", json.dumps(advisory, indent=2) + "\n")
        print(
            f"| tests/fixtures/osv/vulns/{osv_id}.json | advisory {osv_id} "
            f"| https://api.osv.dev/v1/vulns/{osv_id} | {today} | n/a "
            "| make record-fixtures SOURCE=osv | TO CHECK by the Engineer |"
        )
    return 0


def read_cves() -> list[str]:
    """Confirmed CVE ids (one per line) from ``tests/fixtures/cves.txt``."""
    cves: list[str] = []
    if not SIGNAL_CVES.is_file():
        return cves
    for line in SIGNAL_CVES.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            cves.append(line)
    return cves


def record_kev() -> int:
    """Capture a CISA KEV slice for the confirmed CVEs (public feed, no key).

    Fetches the whole catalogue and writes only the fixture CVEs that are listed,
    so the committed slice stays small. Listed state is still accurate: a CVE
    absent from the slice is "not in KEV".
    """
    cves = read_cves()
    if not cves:
        print(f"no CVEs confirmed in {SIGNAL_CVES}; add CVE ids first", file=sys.stderr)
        return 2
    catalogue = KevClient().fetch_catalogue()
    today = dt.date.today().isoformat()
    listed = [c for c in cves if c in catalogue]
    out = {
        "title": "CISA Catalog of Known Exploited Vulnerabilities (fixture slice)",
        "catalogVersion": today,
        "count": len(listed),
        "vulnerabilities": [
            {"cveID": c, "dateAdded": (catalogue.date_added[c].isoformat()
                                       if catalogue.date_added.get(c) else None)}
            for c in listed
        ],
    }
    write(KEV_DIR / "known_exploited_vulnerabilities.json", json.dumps(out, indent=2) + "\n")
    print("| path | fixture | source URL | capture date | check |")
    print(
        f"| tests/fixtures/kev/known_exploited_vulnerabilities.json | KEV slice ({len(listed)} listed) "
        f"| https://www.cisa.gov/.../known_exploited_vulnerabilities.json | {today} "
        "| TO CHECK by the Engineer |"
    )
    return 0


def record_epss() -> int:
    """Capture FIRST EPSS scores for the confirmed CVEs (public API, no key)."""
    cves = read_cves()
    if not cves:
        print(f"no CVEs confirmed in {SIGNAL_CVES}; add CVE ids first", file=sys.stderr)
        return 2
    scores = EpssClient().fetch_scores(cves)
    today = dt.date.today().isoformat()
    data = [
        {
            "cve": c,
            "epss": f"{scores[c].score:.9f}" if scores[c].score is not None else None,
            "percentile": f"{scores[c].percentile:.9f}" if scores[c].percentile is not None else None,
            "date": scores[c].date.isoformat() if scores[c].date else None,
        }
        for c in cves
        if c in scores
    ]
    out = {"status": "OK", "status-code": 200, "total": len(data), "data": data}
    write(EPSS_DIR / "epss.json", json.dumps(out, indent=2) + "\n")
    print("| path | fixture | source URL | capture date | check |")
    print(
        f"| tests/fixtures/epss/epss.json | EPSS scores ({len(data)} CVEs) "
        f"| https://api.first.org/data/v1/epss | {today} | TO CHECK by the Engineer |"
    )
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in (*SOURCES, "all"):
        print("usage: record_fixtures.py <github|osv|kev|epss|all>", file=sys.stderr)
        return 2
    source = argv[1]
    if source == "osv":
        return record_osv()
    if source == "kev":
        return record_kev()
    if source == "epss":
        return record_epss()
    if source == "all":
        return record_github() or record_osv() or record_kev() or record_epss()
    return record_github()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
