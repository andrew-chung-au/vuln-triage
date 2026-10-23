"""Test helpers for authenticated requests through the session guard (#81/#82).

The ``vt_session`` cookie is ``Secure``, which TestClient will not keep in its
jar over http, so these helpers carry the cookie value and the CSRF header
explicitly on each request.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.api.security import COOKIE_NAME, CSRF_HEADER, CSRF_VALUE, hash_password
from vulntriage.db.models import User

PASSWORD = "correct horse battery staple"
CSRF = {CSRF_HEADER: CSRF_VALUE}


def make_user(factory: sessionmaker[Session], *, username: str, role: str,
              email: str, display_name: str = "User") -> int:
    with factory() as session:
        user = User(username=username, display_name=display_name, email=email, role=role,
                    password_hash=hash_password(PASSWORD))
        session.add(user)
        session.commit()
        return user.id


def login_cookie(client: TestClient, username: str, password: str = PASSWORD) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    match = re.search(rf"{COOKIE_NAME}=([^;]+)", response.headers["set-cookie"])
    assert match
    return {COOKIE_NAME: match.group(1)}


def auth_headers(csrf: bool = True) -> dict[str, str]:
    return dict(CSRF) if csrf else {}
