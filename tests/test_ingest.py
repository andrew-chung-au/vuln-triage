"""Ingestion and the scan worker (issue #76), against in-memory SQLite and a fake reader."""

from __future__ import annotations

import json
import threading

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from github_stub import FixtureTransport
from vulntriage.db.enums import ScanTrigger
from vulntriage.db.models import Asset, Base, Dependency, Finding, Lifecycle, Scan
from vulntriage.ingest.github import GitHubReader, RepositoryUnavailable
from vulntriage.ingest.scan import enqueue_scan, run_pending_scans, unfinished_scan_ids
from vulntriage.worker import ScanWorker

SHA = "a" * 40

UV = 'version = 1\n[[package]]\nname = "requests"\nversion = "2.31.0"\n'
NPM = json.dumps(
    {
        "lockfileVersion": 3,
        "packages": {"": {"dependencies": {"left-pad": "1"}}, "node_modules/left-pad": {"version": "1.3.0"}},
    }
)


class FakeReader:
    def __init__(self, files: dict[str, str] | None = None, *, unavailable: bool = False,
                 empty: bool = False) -> None:
        self.files = files or {}
        self.unavailable = unavailable
        self.empty = empty
        self.read_paths: list[str] = []
        self.gate: threading.Event | None = None

    def resolve_commit(self, owner: str, repo: str) -> str | None:
        if self.gate is not None:
            assert self.gate.wait(5)
        if self.unavailable:
            raise RepositoryUnavailable("repository unavailable")
        return None if self.empty else SHA

    def read_file(self, owner: str, repo: str, sha: str, path: str) -> str | None:
        self.read_paths.append(path)
        return self.files.get(path)


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


def make_asset(factory: sessionmaker[Session], url: str = "https://github.com/o/r") -> int:
    with factory() as session:
        asset = Asset(name="a", owner_name=None, owner_email=None, criticality="low",
                      internet_facing=False, repository_url=url)
        session.add(asset)
        session.commit()
        return asset.id


def scan_once(factory: sessionmaker[Session], asset_id: int, reader: FakeReader) -> Scan:
    with factory() as session:
        scan = enqueue_scan(session, session.get(Asset, asset_id), ScanTrigger.PERSON)
        session.commit()
        scan_id = scan.id
    run_pending_scans(factory, reader)
    with factory() as session:
        return session.get(Scan, scan_id)


def deps(factory: sessionmaker[Session], asset_id: int) -> list[tuple[str, str, str | None, str, bool]]:
    with factory() as session:
        rows = session.scalars(select(Dependency).where(Dependency.asset_id == asset_id).order_by(Dependency.id))
        return [(d.ecosystem, d.name, d.version, d.source_file, d.direct) for d in rows]


def asset_of(factory: sessionmaker[Session], asset_id: int) -> Asset:
    with factory() as session:
        return session.get(Asset, asset_id)


def test_all_three_files_are_stored_with_ecosystem_source_and_direct(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    reader = FakeReader({"uv.lock": UV, "requirements.txt": "requests==2.0.0\nflask>=2\n", "package-lock.json": NPM})
    scan = scan_once(factory, aid, reader)
    assert deps(factory, aid) == [
        ("PyPI", "requests", "2.31.0", "uv.lock", False),
        ("PyPI", "requests", "2.0.0", "requirements.txt", True),
        ("PyPI", "flask", None, "requirements.txt", True),
        ("npm", "left-pad", "1.3.0", "package-lock.json", True),
    ]
    asset = asset_of(factory, aid)
    assert asset.last_commit_sha == SHA and asset.last_scan_at is not None
    assert scan.finished_at is not None
    assert [w["kind"] for w in scan.warnings] == ["version unknown"]
    assert set(scan.warnings[0]) == {"kind", "file", "line", "message"}


def test_same_package_in_two_files_is_stored_twice(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    scan_once(factory, aid, FakeReader({"uv.lock": UV, "requirements.txt": "requests==2.31.0\n"}))
    names = [(d[1], d[3]) for d in deps(factory, aid)]
    assert names == [("requests", "uv.lock"), ("requests", "requirements.txt")]


def test_interim_status_rule_must_be_replaced_by_osv_result_in_task_5(factory) -> None:  # type: ignore[no-untyped-def]
    # D3: no OSV matching exists yet. "clean" only means "no warning that makes it incomplete".
    clean = make_asset(factory)
    scan_once(factory, clean, FakeReader({"uv.lock": UV}))
    assert asset_of(factory, clean).scan_status == "scanned, clean"
    assert asset_of(factory, clean).scan_failure_reason is None

    unknown = make_asset(factory)
    scan_once(factory, unknown, FakeReader({"requirements.txt": "pkg\n"}))
    assert asset_of(factory, unknown).scan_status == "scanned, incomplete"

    ignored = make_asset(factory)
    scan = scan_once(factory, ignored, FakeReader({"requirements.txt": "-c c.txt\n--index-url x\npkg==1\n"}))
    assert [w["kind"] for w in scan.warnings] == ["constraints file ignored", "index option ignored"]
    assert asset_of(factory, ignored).scan_status == "scanned, clean"  # these never count
    assert scan.scan_status == "scanned, clean"


def test_no_finding_or_lifecycle_rows_are_created(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    scan_once(factory, aid, FakeReader({"uv.lock": UV}))
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Finding)) == 0
        assert session.scalar(select(func.count()).select_from(Lifecycle)) == 0


def test_second_scan_replaces_the_dependency_set(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    scan_once(factory, aid, FakeReader({"uv.lock": UV}))
    scan_once(factory, aid, FakeReader({"requirements.txt": "flask==3.0.0\n"}))
    assert deps(factory, aid) == [("PyPI", "flask", "3.0.0", "requirements.txt", True)]


def test_failed_ingestion_leaves_existing_rows_unchanged(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    scan_once(factory, aid, FakeReader({"uv.lock": UV}))
    before = deps(factory, aid)
    scan = scan_once(factory, aid, FakeReader({"uv.lock": UV, "package-lock.json": "{bad"}))
    assert deps(factory, aid) == before
    assert scan.scan_status == "scan failed" and scan.failure_reason == "lockfile parse error"
    assert asset_of(factory, aid).scan_status == "scan failed"
    unavailable = scan_once(factory, aid, FakeReader(unavailable=True))
    assert deps(factory, aid) == before and unavailable.failure_reason == "repository unavailable"


def test_unavailable_repository_on_first_scan(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    scan = scan_once(factory, aid, FakeReader(unavailable=True))
    asset = asset_of(factory, aid)
    assert (asset.scan_status, asset.scan_failure_reason) == ("scan failed", "repository unavailable")
    assert scan.finished_at is not None and deps(factory, aid) == []


@pytest.mark.parametrize("reader", [FakeReader({"README.md": "x"}), FakeReader(empty=True)])
def test_no_dependency_files(factory, reader) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    scan = scan_once(factory, aid, reader)
    assert (scan.scan_status, scan.failure_reason) == ("scan failed", "no dependency files")
    assert asset_of(factory, aid).scan_failure_reason == "no dependency files"
    assert deps(factory, aid) == []


def test_parse_error_stores_nothing_from_the_other_files(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    scan = scan_once(factory, aid, FakeReader({"uv.lock": UV, "package-lock.json": '{"lockfileVersion": 1}'}))
    assert scan.failure_reason == "lockfile parse error"
    assert deps(factory, aid) == []


def test_oversized_file_is_a_parse_error(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    big = "# " + "x" * (10 * 1024 * 1024) + "\n"
    scan = scan_once(factory, aid, FakeReader({"requirements.txt": big}))
    assert scan.failure_reason == "lockfile parse error"


def test_stored_url_that_fails_the_pattern_is_never_fetched(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory, url="https://evil.example/o/r")
    reader = FakeReader({"uv.lock": UV})
    scan = scan_once(factory, aid, reader)
    assert scan.failure_reason == "repository unavailable"
    assert reader.read_paths == []


# -- requirements includes ---------------------------------------------------


def test_include_in_a_subdirectory_is_read_relative_to_the_including_file(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    reader = FakeReader({"requirements.txt": "-r sub/a.txt\n", "sub/a.txt": "-r b.txt\nx==1\n", "sub/b.txt": "y==2\n"})
    scan_once(factory, aid, reader)
    assert [(d[1], d[3]) for d in deps(factory, aid)] == [("x", "sub/a.txt"), ("y", "sub/b.txt")]


@pytest.mark.parametrize(
    "target",
    ["/etc/passwd", "../x.txt", "sub/../../x.txt", "https://attacker.example/r.txt", "file:///etc/passwd", "C:\\x.txt"],
)
def test_refused_includes_are_never_read(factory, target: str) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    reader = FakeReader({"requirements.txt": f"-r {target}\npkg==1\n"})
    scan = scan_once(factory, aid, reader)
    assert [(w["kind"], w["file"], w["line"]) for w in scan.warnings] == [("include refused", "requirements.txt", 1)]
    assert target not in json.dumps(scan.warnings)
    assert set(reader.read_paths) == {"uv.lock", "requirements.txt", "package-lock.json"}
    assert asset_of(factory, aid).scan_status == "scanned, incomplete"


def test_include_cycle_terminates(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    reader = FakeReader({"requirements.txt": "-r a.txt\n", "a.txt": "-r b.txt\nx==1\n", "b.txt": "-r a.txt\n-r requirements.txt\ny==2\n"})
    scan = scan_once(factory, aid, reader)
    assert [d[1] for d in deps(factory, aid)] == ["x", "y"]
    assert scan.warnings == []


def test_more_than_20_requirement_files_stops_with_include_refused(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    files = {"requirements.txt": "-r f1.txt\n"}
    for i in range(1, 25):
        files[f"f{i}.txt"] = f"-r f{i + 1}.txt\n"
    reader = FakeReader(files)
    scan = scan_once(factory, aid, reader)
    requirement_reads = [p for p in reader.read_paths if p.endswith(".txt")]
    assert len(requirement_reads) == 20
    assert [(w["kind"], w["message"]) for w in scan.warnings] == [("include refused", "include limit reached")]


def test_missing_in_repository_include_is_a_warning_that_counts(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    scan = scan_once(factory, aid, FakeReader({"requirements.txt": "-r gone.txt\npkg==1\n"}))
    assert [w["kind"] for w in scan.warnings] == ["include not found"]
    assert asset_of(factory, aid).scan_status == "scanned, incomplete"


def test_attacker_index_and_url_make_two_warnings_and_no_extra_read(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    text = "--index-url https://attacker.example/simple\npkg @ https://attacker.example/pkg.whl\n"
    reader = FakeReader({"requirements.txt": text})
    scan = scan_once(factory, aid, reader)
    assert len(scan.warnings) == 2
    assert set(reader.read_paths) == {"uv.lock", "requirements.txt", "package-lock.json"}


# -- fixtures through the real reader ----------------------------------------


@pytest.mark.parametrize(
    ("slug", "expected"),
    [
        ("uv-app", [("requests", "2.31.0"), ("urllib3", "2.0.7")]),
        ("pip-app", [("pytest", "8.0.0"), ("flask", "2.3.3"), ("jinja2", None)]),
        ("npm-app", [("left-pad", "1.3.0"), ("ms", "2.1.3")]),
    ],
)
def test_fixture_repositories_ingest_through_the_github_reader(factory, slug, expected) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory, url=f"https://github.com/fixture-owner/{slug}")
    reader = GitHubReader(FixtureTransport().client(), token_provider=lambda: None)
    with factory() as session:
        enqueue_scan(session, session.get(Asset, aid), ScanTrigger.REGISTRATION)
        session.commit()
    run_pending_scans(factory, reader)
    assert sorted((d[1], d[2]) for d in deps(factory, aid)) == sorted(expected)


# -- queue and worker ---------------------------------------------------------


def test_unfinished_scans_are_found_and_finished_ones_skipped(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    with factory() as session:
        first = enqueue_scan(session, session.get(Asset, aid), ScanTrigger.REGISTRATION)
        session.commit()
        first_id = first.id
    assert unfinished_scan_ids(factory) == [first_id]
    assert run_pending_scans(factory, FakeReader({"uv.lock": UV})) == 1
    assert unfinished_scan_ids(factory) == []
    assert run_pending_scans(factory, FakeReader({"uv.lock": UV})) == 0


def test_registration_scan_row_shape(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    with factory() as session:
        scan = enqueue_scan(session, session.get(Asset, aid), ScanTrigger.REGISTRATION)
        session.commit()
        assert scan.trigger == "registration" and scan.finished_at is None
        assert len(scan.trace_id) == 32 and int(scan.trace_id, 16) >= 0
        assert scan.scan_status == "not yet scanned"


def test_worker_requeues_unfinished_scans_at_start_and_runs_them(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    with factory() as session:
        enqueue_scan(session, session.get(Asset, aid), ScanTrigger.REGISTRATION)
        session.commit()
    reader = FakeReader({"uv.lock": UV})
    worker = ScanWorker(factory, reader)
    worker.start()
    worker.stop()  # the sentinel is queued after the re-queued scan, so the scan finishes first
    assert unfinished_scan_ids(factory) == []
    assert asset_of(factory, aid).scan_status == "scanned, clean"


def test_worker_survives_an_unexpected_error(factory) -> None:  # type: ignore[no-untyped-def]
    class Boom(FakeReader):
        def resolve_commit(self, owner: str, repo: str) -> str | None:
            raise ValueError("bug")

    aid = make_asset(factory)
    with factory() as session:
        enqueue_scan(session, session.get(Asset, aid), ScanTrigger.REGISTRATION)
        session.commit()
    worker = ScanWorker(factory, Boom())
    worker.start()
    worker.stop()
    assert len(unfinished_scan_ids(factory)) == 1  # left unfinished, re-queued at next start-up
