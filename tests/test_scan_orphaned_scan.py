"""#194: a scan whose asset row is gone logs no ``scan.finished`` line.

The orphaned-scan scenario needs SQLite's ``PRAGMA foreign_keys=OFF`` to build:
with foreign keys enforced (Postgres, or SQLite's default here) a scan row cannot
outlive its asset. So this case is ``unit`` only (SQLite, in ``make verify``) and
is not selected by the Postgres ``sqlite_integration`` job.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from test_ingest import UV, FakeReader, make_asset
from vulntriage.db.enums import ScanTrigger
from vulntriage.db.models import Asset, Base
from vulntriage.ingest.scan import enqueue_scan, run_scan

pytestmark = pytest.mark.unit


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    assert sqlite_engine.dialect.name == "sqlite"
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


class CleanOsv:
    def query_batch(self, queries: list[Any]) -> list[list[Any]]:
        return [[] for _ in queries]

    def get_vuln(self, osv_id: str) -> dict[str, Any]:
        raise AssertionError("no advisories expected")


def _finished(out: str) -> list[dict[str, Any]]:
    lines = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    return [r for r in lines if r["event"] == "scan.finished"]


def test_scan_with_missing_asset_logs_nothing(factory, capsys) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    with factory() as session:
        scan = enqueue_scan(session, session.get(Asset, aid), ScanTrigger.PERSON)
        session.commit()
        scan_id = scan.id
    with factory() as session:
        # The foreign key is enforced, so switch it off for this connection
        # (before any write opens a transaction) to orphan the scan.
        session.execute(text("PRAGMA foreign_keys=OFF"))
        session.execute(text("DELETE FROM assets WHERE id = :id"), {"id": aid})
        session.commit()
        session.execute(text("PRAGMA foreign_keys=ON"))
    capsys.readouterr()
    run_scan(factory, FakeReader({"uv.lock": UV}), scan_id, CleanOsv())
    assert _finished(capsys.readouterr().out) == []
