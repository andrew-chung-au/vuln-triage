"""Authentication routes: login, logout and the current user (issue #81, task 9a)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.api.security import (
    COOKIE_NAME,
    LoginThrottle,
    clear_session_cookie,
    create_session,
    delete_session,
    require_session,
    set_session_cookie,
    verify_password,
)
from vulntriage.db.models import User

router = APIRouter(tags=["auth"])

_BAD_LOGIN = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "unauthenticated", "message": "Invalid username or password."},
)


class LoginRequest(BaseModel):
    """Strict ``{username, password}`` (``_docs/openapi.yaml``: LoginRequest)."""

    model_config = ConfigDict(extra="forbid", strict=True)

    username: str
    password: str


def user_to_wire(user: User) -> dict[str, object]:
    """The contract ``User`` (camelCase). ``password_hash`` stays server-side."""
    return {
        "id": str(user.id),
        "username": user.username,
        "displayName": user.display_name,
        "email": user.email,
        "role": user.role,
    }


@router.post("/auth/login")
def login(body: LoginRequest, request: Request, response: Response) -> dict[str, object]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    throttle: LoginThrottle = request.app.state.login_throttle

    # A locked username returns the same 401 as a wrong password, before any
    # password check, so the response never reveals whether the username exists.
    if throttle.is_locked(body.username):
        raise _BAD_LOGIN

    with factory() as session:
        user = session.scalar(select(User).where(User.username == body.username))
        if user is None or not verify_password(user.password_hash, body.password):
            throttle.record_failure(body.username)
            raise _BAD_LOGIN
        throttle.clear(body.username)
        raw = create_session(session, user)
        wire = user_to_wire(user)
        session.commit()

    set_session_cookie(response, raw)
    return wire


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response) -> Response:
    # Idempotent and needs no session or CSRF header: it only clears the caller's
    # own cookie and deletes the matching session row if there is one.
    raw = request.cookies.get(COOKIE_NAME)
    if raw:
        factory: sessionmaker[Session] = request.app.state.session_factory
        with factory() as session:
            delete_session(session, raw)
            session.commit()
    clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/auth/me")
def current_user(user: User = Depends(require_session)) -> dict[str, object]:
    return user_to_wire(user)
