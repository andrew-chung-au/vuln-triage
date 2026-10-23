"""Session auth and CSRF (issue #81, task 9a): I-AUTH-SESSION and the guard cases."""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi import Depends, Request
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.api.security import (
    ABSOLUTE_LIFETIME,
    COOKIE_NAME,
    IDLE_LIFETIME,
    LoginThrottle,
    hash_password,
    may_accept_risk,
    require_session,
)
from vulntriage.db.models import AuthSession, Base, User

pytestmark = pytest.mark.sqlite_integration  # task 13: the SQLite I-* integration layer
from vulntriage.main import create_app

PASSWORD = "correct horse battery staple"


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


def _make_user(factory: sessionmaker[Session], *, username: str = "lead",
               role: str = "security lead", email: str = "lead@example.com") -> int:
    with factory() as session:
        user = User(username=username, display_name="Lead", email=email, role=role,
                    password_hash=hash_password(PASSWORD))
        session.add(user)
        session.commit()
        return user.id


def _client(factory: sessionmaker[Session]) -> TestClient:
    # A route that requires a session, to exercise the guard (resource routes are #82).
    app = create_app(factory, reader=None, run_worker=False)

    @app.post("/_guarded")
    def _guarded(user: User = Depends(require_session)) -> dict[str, str]:  # type: ignore[no-untyped-def]
        return {"user": user.username}

    @app.get("/_guarded")
    def _guarded_get(user: User = Depends(require_session)) -> dict[str, str]:  # type: ignore[no-untyped-def]
        return {"user": user.username}

    return TestClient(app)


def _login(client: TestClient, username: str = "lead", password: str = PASSWORD):  # type: ignore[no-untyped-def]
    return client.post("/auth/login", json={"username": username, "password": password})


def _cookie_of(response) -> str:  # type: ignore[no-untyped-def]
    """The raw vt_session value from a login Set-Cookie header.

    TestClient speaks http://testserver and will not store a `Secure` cookie in
    its jar, so tests carry the value explicitly on later requests instead.
    """
    import re

    match = re.search(rf"{COOKIE_NAME}=([^;]+)", response.headers["set-cookie"])
    assert match, response.headers.get("set-cookie")
    return match.group(1)


def _session_cookie(client: TestClient, **kw) -> dict[str, str]:  # type: ignore[no-untyped-def]
    return {COOKIE_NAME: _cookie_of(_login(client, **kw))}


# -- login ------------------------------------------------------------------


def test_login_sets_httponly_secure_samesite_cookie_and_returns_user(factory) -> None:  # type: ignore[no-untyped-def]
    _make_user(factory)
    client = _client(factory)
    response = _login(client)
    assert response.status_code == 200
    assert response.json() == {
        "id": response.json()["id"], "username": "lead", "displayName": "Lead",
        "email": "lead@example.com", "role": "security lead",
    }
    assert "password" not in response.text and "hash" not in response.text
    set_cookie = response.headers["set-cookie"].lower()  # attribute casing is cosmetic
    assert COOKIE_NAME in set_cookie
    assert "httponly" in set_cookie and "secure" in set_cookie and "samesite=strict" in set_cookie


def test_login_stores_only_the_hash_of_the_cookie_value(factory) -> None:  # type: ignore[no-untyped-def]
    _make_user(factory)
    client = _client(factory)
    raw = _cookie_of(_login(client))
    with factory() as session:
        rows = list(session.scalars(select(AuthSession)))
    assert len(rows) == 1
    assert rows[0].id != raw  # the stored id is the hash, not the cookie value


@pytest.mark.parametrize("body", [
    {"username": "lead"},  # missing password
    {"username": "lead", "password": PASSWORD, "extra": 1},  # extra field
    {"username": "lead", "password": 123},  # wrong type
])
def test_login_malformed_body_is_422(factory, body) -> None:  # type: ignore[no-untyped-def]
    _make_user(factory)
    response = _client(factory).post("/auth/login", json=body)
    assert response.status_code == 422
    assert response.json() == {"code": "validation", "message": "The request is invalid."}


def test_wrong_password_and_unknown_user_are_the_same_401(factory) -> None:  # type: ignore[no-untyped-def]
    _make_user(factory)
    client = _client(factory)
    wrong = _login(client, password="nope")
    unknown = _login(client, username="ghost")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {
        "code": "unauthenticated", "message": "Invalid username or password."}


def test_five_failures_lock_the_username_for_15_minutes(factory) -> None:  # type: ignore[no-untyped-def]
    _make_user(factory)
    client = _client(factory)
    for _ in range(5):
        assert _login(client, password="nope").status_code == 401
    # Even the correct password is now refused with the same 401.
    locked = _login(client, password=PASSWORD)
    assert locked.status_code == 401
    assert locked.json()["code"] == "unauthenticated"


def test_lock_only_affects_the_targeted_username(factory) -> None:  # type: ignore[no-untyped-def]
    _make_user(factory, username="lead")
    _make_user(factory, username="owner", role="asset owner", email="o@example.com")
    client = _client(factory)
    for _ in range(5):
        _login(client, username="lead", password="nope")
    assert _login(client, username="owner").status_code == 200


# -- /auth/me and logout ----------------------------------------------------


def test_me_returns_the_user_with_a_session_and_401_without(factory) -> None:  # type: ignore[no-untyped-def]
    _make_user(factory)
    client = _client(factory)
    assert client.get("/auth/me").status_code == 401
    cookies = _session_cookie(client)
    me = client.get("/auth/me", cookies=cookies)
    assert me.status_code == 200 and me.json()["username"] == "lead"


def test_logout_clears_the_session_and_is_idempotent(factory) -> None:  # type: ignore[no-untyped-def]
    _make_user(factory)
    client = _client(factory)
    cookies = _session_cookie(client)
    assert client.post("/auth/logout", cookies=cookies).status_code == 204
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(AuthSession)) == 0
    # A second logout with no session still succeeds and needs no CSRF header.
    assert client.post("/auth/logout").status_code == 204
    # The cleared session no longer authenticates.
    assert client.get("/auth/me", cookies=cookies).status_code == 401


# -- the guard: CSRF, wrong consumer, expiry --------------------------------


def test_non_get_requires_the_csrf_header(factory) -> None:  # type: ignore[no-untyped-def]
    _make_user(factory)
    client = _client(factory)
    cookies = _session_cookie(client)
    # No X-Requested-With header -> 403, changes nothing.
    assert client.post("/_guarded", cookies=cookies).status_code == 403
    assert client.post("/_guarded", cookies=cookies,
                       headers={"X-Requested-With": "nope"}).status_code == 403
    ok = client.post("/_guarded", cookies=cookies, headers={"X-Requested-With": "XMLHttpRequest"})
    assert ok.status_code == 200 and ok.json() == {"user": "lead"}


def test_get_does_not_require_the_csrf_header(factory) -> None:  # type: ignore[no-untyped-def]
    _make_user(factory)
    client = _client(factory)
    cookies = _session_cookie(client)
    assert client.get("/_guarded", cookies=cookies).status_code == 200


def test_no_session_is_401(factory) -> None:  # type: ignore[no-untyped-def]
    _make_user(factory)
    client = _client(factory)
    assert client.get("/_guarded").status_code == 401


def test_service_bearer_token_on_a_frontend_operation_is_403(factory) -> None:  # type: ignore[no-untyped-def]
    _make_user(factory)
    client = _client(factory)
    # A valid-looking bearer credential (wrong consumer) and no session -> 403.
    response = client.get("/_guarded", headers={"Authorization": "Bearer service-token"})
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_expired_or_logged_out_session_is_401(factory) -> None:  # type: ignore[no-untyped-def]
    _make_user(factory)
    client = _client(factory)
    cookies = _session_cookie(client)
    # Age the session past its absolute lifetime, as the clock would.
    with factory() as session:
        row = session.scalar(select(AuthSession))
        old = dt.datetime.now(dt.UTC) - ABSOLUTE_LIFETIME - dt.timedelta(minutes=1)
        row.created_at = old
        row.last_seen_at = old
        row.expires_at = old + ABSOLUTE_LIFETIME
        session.commit()
    assert client.get("/_guarded", cookies=cookies).status_code == 401
    # The expired row was deleted on that attempt.
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(AuthSession)) == 0


def test_idle_timeout_expires_the_session(factory) -> None:  # type: ignore[no-untyped-def]
    _make_user(factory)
    client = _client(factory)
    cookies = _session_cookie(client)
    with factory() as session:
        row = session.scalar(select(AuthSession))
        row.last_seen_at = dt.datetime.now(dt.UTC) - IDLE_LIFETIME - dt.timedelta(minutes=1)
        session.commit()
    assert client.get("/_guarded", cookies=cookies).status_code == 401


# -- owner-match rule (A30) -------------------------------------------------


def test_security_lead_may_accept_on_any_asset(factory) -> None:  # type: ignore[no-untyped-def]
    lead = User(username="l", display_name="L", email="l@x.com", role="security lead",
                password_hash="x")
    assert may_accept_risk(lead, "someone@else.com") is True
    assert may_accept_risk(lead, None) is True


def test_asset_owner_may_accept_only_on_a_matching_email() -> None:
    owner = User(username="o", display_name="O", email="Owner@Example.com ", role="asset owner",
                 password_hash="x")
    assert may_accept_risk(owner, "owner@example.com") is True  # trim + case-fold
    assert may_accept_risk(owner, "  OWNER@EXAMPLE.COM") is True
    assert may_accept_risk(owner, "other@example.com") is False
    assert may_accept_risk(owner, None) is False


def test_throttle_window_and_clear() -> None:
    throttle = LoginThrottle()
    now = dt.datetime(2026, 1, 1, 12, 0, tzinfo=dt.UTC)
    for i in range(4):
        throttle.record_failure("u", now + dt.timedelta(seconds=i))
    assert throttle.is_locked("u", now + dt.timedelta(seconds=5)) is False
    throttle.record_failure("u", now + dt.timedelta(seconds=5))  # 5th within the window
    assert throttle.is_locked("u", now + dt.timedelta(seconds=6)) is True
    throttle.clear("u")
    assert throttle.is_locked("u", now + dt.timedelta(seconds=7)) is False
