"""The operator user-creation command (task 9 defect #176).

Covers task 9's check — "a user created by the command signing in while the
stored password value is an Argon2id hash and not the password" — plus the
non-interactive (piped-stdin) and interactive (tty) password paths, role
validation, duplicate rejection, and that the password is never a command-line
argument. All under `make test` (SQLite, no Docker, no network).
"""

from __future__ import annotations

import io

import pytest
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.api.security import verify_password
from vulntriage.db.models import Base, User
from vulntriage.manage import (
    UserCreationError,
    build_parser,
    create_user,
    read_password,
)

# No module-level pytestmark: the read_password/parser cases are `unit`; the
# create_user DB cases are `sqlite_integration`. Each is marked explicitly so no
# case carries both markers.

_PASSWORD = "correct horse battery staple"


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


# -- the password-reading seam (both paths, no real tty needed) ----------------


@pytest.mark.unit
def test_read_password_from_stdin_when_no_terminal() -> None:
    # Piped input (Compose/CI): one line on stdin, newline stripped.
    stdin = io.StringIO(_PASSWORD + "\n")
    got = read_password(stdin=stdin, isatty=lambda: False)
    assert got == _PASSWORD


@pytest.mark.unit
def test_read_password_prompts_when_terminal_attached() -> None:
    # tty: getpass is used (injected), stdin is not read.
    prompts: list[str] = []

    def fake_getpass(prompt: str) -> str:
        prompts.append(prompt)
        return _PASSWORD

    got = read_password(stdin=io.StringIO(""), isatty=lambda: True, getpass_fn=fake_getpass)
    assert got == _PASSWORD
    assert prompts, "getpass was not called in the tty path"


@pytest.mark.unit
def test_read_password_empty_stdin_errors() -> None:
    with pytest.raises(UserCreationError):
        read_password(stdin=io.StringIO(""), isatty=lambda: False)  # EOF, no terminal
    with pytest.raises(UserCreationError):
        read_password(stdin=io.StringIO("\n"), isatty=lambda: False)  # empty line


# -- the command never accepts a password on the command line ------------------


@pytest.mark.unit
def test_create_user_parser_has_no_password_argument() -> None:
    parser = build_parser()
    # --password must not be a recognised option (password is never on argv).
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["create-user", "--username", "u", "--display-name", "D",
             "--email", "e@x", "--role", "security lead", "--password", "x"]
        )


@pytest.mark.unit
def test_create_user_parser_rejects_unknown_role() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["create-user", "--username", "u", "--display-name", "D",
             "--email", "e@x", "--role", "admin"]
        )


# -- create_user: the Argon2id hash + sign-in (task 9's check) -----------------


@pytest.mark.sqlite_integration
def test_create_user_stores_argon2_hash_not_the_password(factory) -> None:  # type: ignore[no-untyped-def]
    user_id = create_user(
        factory, username="lead", display_name="Lead", email="lead@x",
        role="security lead", password=_PASSWORD,
    )
    with factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        # The stored value is an Argon2id hash, never the plaintext.
        assert user.password_hash != _PASSWORD
        assert user.password_hash.startswith("$argon2id$"), user.password_hash
        # And it verifies the password (so the created user can sign in).
        assert verify_password(user.password_hash, _PASSWORD) is True
        assert user.role == "security lead"


@pytest.mark.sqlite_integration
def test_create_user_rejects_unknown_role(factory) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(UserCreationError):
        create_user(
            factory, username="u", display_name="D", email="e@x",
            role="admin", password=_PASSWORD,
        )


@pytest.mark.sqlite_integration
def test_create_user_rejects_duplicate_username(factory) -> None:  # type: ignore[no-untyped-def]
    create_user(
        factory, username="dup", display_name="D", email="e@x",
        role="asset owner", password=_PASSWORD,
    )
    with pytest.raises(UserCreationError):
        create_user(
            factory, username="dup", display_name="D2", email="e2@x",
            role="asset owner", password=_PASSWORD,
        )
