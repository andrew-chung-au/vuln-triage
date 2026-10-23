"""I-ASSET (POST /assets only; the reads are #82), against in-memory SQLite."""

from __future__ import annotations

import threading
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from test_ingest import FakeReader
from vulntriage.db.models import Asset, Base, Scan
from vulntriage.ingest.scan import run_pending_scans
from vulntriage.main import create_app

URL = "https://github.com/octo/repo"
BODY: dict[str, Any] = {
    "name": "Payments",
    "ownerName": "Ada",
    "ownerEmail": "ada@example.com",
    "criticality": "high",
    "internetFacing": True,
    "repositoryUrl": URL,
}


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


def counts(factory: sessionmaker[Session]) -> tuple[int, int]:
    with factory() as s:
        return (
            s.scalar(select(func.count()).select_from(Asset)),
            s.scalar(select(func.count()).select_from(Scan)),
        )


def post(factory: sessionmaker[Session], reader: FakeReader, body: Any) -> Any:
    client = TestClient(create_app(factory, reader, run_worker=False))
    return client.post("/assets", json=body)


def test_valid_registration_returns_201_with_an_asset(factory) -> None:  # type: ignore[no-untyped-def]
    reader = FakeReader({"uv.lock": "version = 1\n"})
    response = post(factory, reader, BODY)
    assert response.status_code == 201
    data = response.json()
    assert isinstance(data["id"], str)
    assert data == {
        "id": data["id"],
        "name": "Payments",
        "ownerName": "Ada",
        "ownerEmail": "ada@example.com",
        "criticality": "high",
        "internetFacing": True,
        "repositoryUrl": URL,
        "scanStatus": "not yet scanned",
        "scanFailureReason": None,
        "lastScanAt": None,
        "lastCommitSha": None,
        "scanWarnings": [],
    }
    with factory() as s:
        row = s.get(Asset, int(data["id"]))
        assert (row.name, row.owner_name, row.owner_email, row.criticality) == ("Payments", "Ada", "ada@example.com", "high")
        assert row.internet_facing is True and row.repository_url == URL
        assert row.scan_status == "not yet scanned"
        scan = s.scalars(select(Scan)).one()
        assert scan.trigger == "registration" and scan.finished_at is None
        assert len(scan.trace_id) == 32 and int(scan.trace_id, 16) >= 0
    assert reader.read_paths == []  # nothing is read during the request


@pytest.mark.parametrize(
    ("name", "email", "expect_name", "expect_email"),
    [
        (None, None, None, None),
        ("", "", None, None),
        ("   ", "  ", None, None),
        ("Ada", None, "Ada", None),
        (None, "ada@example.com", None, "ada@example.com"),
        (" Ada ", " ada@example.com ", "Ada", "ada@example.com"),
    ],
)
def test_owner_fields_unset_are_stored_null(factory, name, email, expect_name, expect_email) -> None:  # type: ignore[no-untyped-def]
    body = {**BODY, "ownerName": name, "ownerEmail": email}
    response = post(factory, FakeReader(), body)
    assert response.status_code == 201
    assert response.json()["ownerName"] == expect_name and response.json()["ownerEmail"] == expect_email
    with factory() as s:
        row = s.scalars(select(Asset)).one()
        assert (row.owner_name, row.owner_email) == (expect_name, expect_email)


def test_the_201_returns_before_the_scan_runs(factory) -> None:  # type: ignore[no-untyped-def]
    reader = FakeReader({"uv.lock": "version = 1\n"})
    reader.gate = threading.Event()
    with TestClient(create_app(factory, reader, run_worker=True)) as client:
        response = client.post("/assets", json=BODY)
        assert response.status_code == 201
        assert response.json()["scanStatus"] == "not yet scanned"
        with factory() as s:
            assert s.scalars(select(Scan)).one().finished_at is None
            assert s.scalars(select(Asset)).one().scan_status == "not yet scanned"
        reader.gate.set()
    # leaving the context stops the worker after it finished the queued scan
    with factory() as s:
        assert s.scalars(select(Scan)).one().finished_at is not None
        assert s.scalars(select(Asset)).one().scan_status == "scanned, clean"


def test_run_pending_scans_finishes_a_registered_scan(factory) -> None:  # type: ignore[no-untyped-def]
    reader = FakeReader({"uv.lock": "version = 1\n"})
    post(factory, reader, BODY)
    assert run_pending_scans(factory, reader) == 1
    with factory() as s:
        assert s.scalars(select(Scan)).one().finished_at is not None


BAD_URLS = [
    "http://github.com/o/r",
    "https://github.com/o/r.git",
    "https://github.com/o/r/",
    "https://github.com/o/r/tree/main",
    "https://github.com.evil.example/o/r",
    "https://user@github.com/o/r",
    "git@github.com:o/r.git",
    "/home/me/project",
    "file:///etc/passwd",
    "",
    "https://github.com/o/r\n",
    "https://GITHUB.com/o/r",
]


@pytest.mark.parametrize("url", BAD_URLS)
def test_bad_repository_urls_are_refused(factory, url: str) -> None:  # type: ignore[no-untyped-def]
    assert_refused(factory, {**BODY, "repositoryUrl": url}, secret=url)


def test_missing_repository_url_is_refused(factory) -> None:  # type: ignore[no-untyped-def]
    body = {k: v for k, v in BODY.items() if k != "repositoryUrl"}
    assert_refused(factory, body)


@pytest.mark.parametrize(
    "change",
    [
        {"extra": "x"},
        {"path": "/srv/code"},
        {"criticality": "urgent"},
        {"internetFacing": "yes"},
        {"internetFacing": 1},
        {"ownerEmail": "not-an-email"},
        {"ownerEmail": "a@b"},
        {"ownerEmail": "a b@example.com"},
        {"name": "   "},
        {"name": ""},
        {"name": None},
        {"ownerName": 5},
    ],
)
def test_other_invalid_bodies_are_refused(factory, change: dict[str, Any]) -> None:  # type: ignore[no-untyped-def]
    secret = change.get("ownerEmail")
    assert_refused(factory, {**BODY, **change}, secret=secret if isinstance(secret, str) else None)


@pytest.mark.parametrize("missing", ["name", "ownerName", "ownerEmail", "criticality", "internetFacing"])
def test_every_key_is_required(factory, missing: str) -> None:  # type: ignore[no-untyped-def]
    assert_refused(factory, {k: v for k, v in BODY.items() if k != missing})


def test_non_json_and_non_object_bodies_are_refused(factory) -> None:  # type: ignore[no-untyped-def]
    client = TestClient(create_app(factory, FakeReader(), run_worker=False))
    for kwargs in ({"content": "{nope", "headers": {"content-type": "application/json"}}, {"json": []}):
        response = client.post("/assets", **kwargs)
        assert response.status_code == 422
        assert response.json()["code"] == "validation"
    assert counts(factory) == (0, 0)


def assert_refused(factory, body: Any, secret: str | None = None) -> None:  # type: ignore[no-untyped-def]
    reader = FakeReader()
    response = post(factory, reader, body)
    assert response.status_code == 422
    data = response.json()
    assert set(data) == {"code", "message"} and data["code"] == "validation" and data["message"]
    if secret:
        assert secret not in response.text
    assert "ada@example.com" not in response.text and "github.com" not in response.text
    assert counts(factory) == (0, 0)
    assert reader.read_paths == []


def test_openapi_document_has_no_local_path_or_upload_field() -> None:
    from pathlib import Path

    text = (Path(__file__).resolve().parent.parent / "_docs" / "openapi.yaml").read_text()
    start = text.index("    NewAssetInput:")
    block = text[start : text.index("    AssetUpdateInput:")]
    assert "additionalProperties: false" in block
    for word in ("path", "upload", "file"):
        assert f"        {word}" not in block
