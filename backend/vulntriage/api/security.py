"""Session authentication, CSRF and the owner-match rule (issue #81, task 9a).

The frontend authenticates with the ``vt_session`` cookie (``cookieAuth``), set
by ``POST /auth/login`` and cleared by ``POST /auth/logout``. There is no bearer
token for the frontend; the service credentials (n8n, MCP, responder) are task
10a/10b. All values are A30 (``_docs/architecture.md`` § Security boundaries) and
``_docs/api.md`` § Authentication.

Design:
- The cookie carries a random 256-bit id (``secrets.token_urlsafe(32)``). Only
  its SHA-256 hash is stored, as the ``sessions`` table primary key, so a leaked
  database row cannot be replayed as a cookie.
- A session is valid for 30 minutes idle (``last_seen_at``) and 8 hours absolute
  (``created_at``); each authenticated request bumps ``last_seen_at``.
- Passwords are verified with Argon2id (``argon2-cffi``). The operator command
  that creates users and hashes passwords is task 9's other half.
- Five failed logins for a username in 15 minutes lock it for 15 minutes; a
  locked username returns the same ``401`` as a wrong password, so the response
  never reveals whether the username exists. The counter is in-process (one
  backend; no table is required by the spec).
- Every cookie-authenticated non-GET request except login and logout must carry
  ``X-Requested-With: XMLHttpRequest`` (CSRF); a missing or different value is
  ``403`` and changes nothing.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import secrets
import threading
from dataclasses import dataclass, field

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException, Request, Response, status
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.db.models import AuthSession, User

COOKIE_NAME = "vt_session"
CSRF_HEADER = "X-Requested-With"
CSRF_VALUE = "XMLHttpRequest"

IDLE_LIFETIME = dt.timedelta(minutes=30)
ABSOLUTE_LIFETIME = dt.timedelta(hours=8)
LOCKOUT_THRESHOLD = 5
LOCKOUT_WINDOW = dt.timedelta(minutes=15)
LOCKOUT_DURATION = dt.timedelta(minutes=15)

_hasher = PasswordHasher()


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


# -- password hashing -------------------------------------------------------


def hash_password(password: str) -> str:
    """Argon2id hash for the operator command (task 9's user-creation half)."""
    return _hasher.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    # verify() returns True or raises; a wrong password is VerificationError
    # (VerifyMismatchError subclasses it), a malformed/empty stored hash is
    # InvalidHashError (or a decode ValueError/TypeError on odd input).
    try:
        return _hasher.verify(stored_hash, password)
    except (VerificationError, InvalidHashError, ValueError, TypeError):
        return False


# -- session ids ------------------------------------------------------------


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_session_token() -> tuple[str, str]:
    """Return (raw cookie value, stored id = its SHA-256 hash)."""
    raw = secrets.token_urlsafe(32)  # 256 bits of entropy
    return raw, _hash_token(raw)


# -- login lockout (in-process) ---------------------------------------------


@dataclass
class LoginThrottle:
    """Per-username failed-login counter with a sliding window and a lock."""

    _failures: dict[str, list[dt.datetime]] = field(default_factory=dict)
    _locked_until: dict[str, dt.datetime] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def is_locked(self, username: str, now: dt.datetime | None = None) -> bool:
        now = now or _now()
        with self._lock:
            until = self._locked_until.get(username)
            return until is not None and until > now

    def record_failure(self, username: str, now: dt.datetime | None = None) -> None:
        now = now or _now()
        with self._lock:
            window = [t for t in self._failures.get(username, []) if t > now - LOCKOUT_WINDOW]
            window.append(now)
            self._failures[username] = window
            if len(window) >= LOCKOUT_THRESHOLD:
                self._locked_until[username] = now + LOCKOUT_DURATION

    def clear(self, username: str) -> None:
        with self._lock:
            self._failures.pop(username, None)
            self._locked_until.pop(username, None)


# -- session lifecycle ------------------------------------------------------


def create_session(session: Session, user: User) -> str:
    """Persist a new session for ``user`` and return the raw cookie value."""
    raw, stored_id = new_session_token()
    now = _now()
    session.add(
        AuthSession(
            id=stored_id,
            user_id=user.id,
            created_at=now,
            last_seen_at=now,
            expires_at=now + ABSOLUTE_LIFETIME,
        )
    )
    return raw


def set_session_cookie(response: Response, raw: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        raw,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
        max_age=int(ABSOLUTE_LIFETIME.total_seconds()),
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=True, samesite="strict")


def resolve_session(session: Session, raw: str, now: dt.datetime | None = None) -> User | None:
    """Return the live session's user, bumping ``last_seen_at``; else None.

    A session past its idle or absolute lifetime is deleted and treated as
    invalid, so a later request with the same cookie also fails.
    """
    now = now or _now()
    stored = session.get(AuthSession, _hash_token(raw))
    if stored is None:
        return None
    idle_cutoff = stored.last_seen_at + IDLE_LIFETIME
    if now >= stored.expires_at or now >= idle_cutoff:
        session.delete(stored)
        return None
    stored.last_seen_at = now
    return session.get(User, stored.user_id)


def delete_session(session: Session, raw: str) -> None:
    stored = session.get(AuthSession, _hash_token(raw))
    if stored is not None:
        session.delete(stored)


# -- the request guard ------------------------------------------------------

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "unauthenticated", "message": "No valid session."},
)
_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"code": "forbidden", "message": "The request is not allowed."},
)

_SERVICE_SCHEMES = ("authorization",)  # a bearer token on a frontend op is 403, not 401


def require_session(request: Request) -> User:
    """FastAPI dependency: the signed-in user for a cookie-authenticated operation.

    Order (``_docs/api.md`` § Status codes): ``401`` for no/expired/invalid
    session; then ``403`` for a wrong-consumer credential or a missing/wrong CSRF
    header on a non-GET request (login and logout do not use this dependency).
    """
    factory: sessionmaker[Session] = request.app.state.session_factory
    raw = request.cookies.get(COOKIE_NAME)

    # A valid service token (bearer) on a frontend operation is 403, not 401 —
    # but only once we know there is no usable session. A request with neither a
    # session cookie nor any credential is 401.
    has_bearer = request.headers.get("authorization") is not None

    if not raw:
        raise _FORBIDDEN if has_bearer else _UNAUTHENTICATED

    user = _resolve_in_txn(factory, raw)
    if user is None:
        raise _FORBIDDEN if has_bearer else _UNAUTHENTICATED

    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if request.headers.get(CSRF_HEADER) != CSRF_VALUE:
            raise _FORBIDDEN
    return user


def _resolve_in_txn(factory: sessionmaker[Session], raw: str) -> User | None:
    with factory() as session:
        user = resolve_session(session, raw)
        session.commit()
        return user


# -- owner-match rule (A30) -------------------------------------------------


def _normalise_email(value: str | None) -> str:
    return (value or "").strip().casefold()


def may_accept_risk(user: User, asset_owner_email: str | None) -> bool:
    """A30: a security lead may accept on any asset; an asset owner only on
    assets whose owner email matches theirs after trimming and case-folding."""
    from vulntriage.db.enums import UserRole

    if user.role == UserRole.SECURITY_LEAD.value:
        return True
    user_email = _normalise_email(user.email)
    return bool(user_email) and user_email == _normalise_email(asset_owner_email)
