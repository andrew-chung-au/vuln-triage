"""Operator commands (task 9's user-creation half; defect #176).

There is no sign-up: a dashboard user is created only by an operator running this
command, which the dev, prod and local-demo environments need to have anyone
sign in. Task 9's wording: it "creates a dashboard user (username, display name,
email, role and a password read from a prompt, never from the command line)",
and its check is "a user created by the command signing in while the stored
password value is an Argon2id hash and not the password".

Usage:
    python -m vulntriage.manage create-user --username U --display-name "D" \\
        --email e@x --role "security lead"

The password is NEVER a command-line argument. It is read from an interactive
prompt when a terminal is attached (``getpass``), or from stdin when one is not
(so Compose/CI can pipe it: ``docker compose run -T backend python -m
vulntriage.manage create-user ... < password-file``). The stored value is an
Argon2id hash (``api.security.hash_password``), never the plaintext.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Callable
from typing import TextIO

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.api.security import hash_password
from vulntriage.db.enums import UserRole
from vulntriage.db.models import User
from vulntriage.db.session import create_db_engine, create_session_factory

_ROLE_VALUES = tuple(r.value for r in UserRole)


class UserCreationError(RuntimeError):
    """A create-user command could not complete (bad role, duplicate, empty password)."""


def read_password(
    *,
    stdin: TextIO | None = None,
    isatty: Callable[[], bool] | None = None,
    getpass_fn: Callable[[str], str] = getpass.getpass,
) -> str:
    """Read the password from a prompt (tty) or from stdin (piped).

    Never from the command line. When a terminal is attached, prompt with
    ``getpass`` (no echo). When not (Compose/CI piping input), read one line from
    stdin and strip the trailing newline. The seams (``stdin``/``isatty``/
    ``getpass_fn``) are injectable so both paths are unit-testable without a tty.

    VERIFY: ``getpass.getpass`` with no terminal may fall back to stdin with a
    warning on some platforms; the explicit isatty branch avoids relying on that.
    """
    stream = stdin if stdin is not None else sys.stdin
    at_tty = isatty() if isatty is not None else stream.isatty()
    if at_tty:
        password = getpass_fn("Password: ")
    else:
        line = stream.readline()
        if line == "":
            raise UserCreationError("no password on stdin (and no terminal to prompt)")
        password = line.rstrip("\n")
    if not password:
        raise UserCreationError("password must not be empty")
    return password


def create_user(
    factory: sessionmaker[Session],
    *,
    username: str,
    display_name: str,
    email: str,
    role: str,
    password: str,
) -> int:
    """Insert one dashboard user with an Argon2id password hash; return its id.

    Validates the role against :class:`UserRole` and rejects a duplicate
    username (the unique constraint) with a clear error. The password is hashed
    with :func:`vulntriage.api.security.hash_password` (Argon2id); the plaintext
    is never stored or logged.
    """
    if role not in _ROLE_VALUES:
        raise UserCreationError(f"role must be one of {_ROLE_VALUES}; got {role!r}")
    user = User(
        username=username,
        display_name=display_name,
        email=email,
        role=role,
        password_hash=hash_password(password),
    )
    try:
        with factory() as session:
            session.add(user)
            session.commit()
            return user.id
    except IntegrityError as exc:
        raise UserCreationError(f"could not create user {username!r} (duplicate username?)") from exc


def _cmd_create_user(args: argparse.Namespace) -> int:
    password = read_password()
    factory = create_session_factory(create_db_engine())
    user_id = create_user(
        factory,
        username=args.username,
        display_name=args.display_name,
        email=args.email,
        role=args.role,
        password=password,
    )
    print(f"created user {args.username!r} (id {user_id}, role {args.role!r})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m vulntriage.manage")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-user", help="create a dashboard user (password read from a prompt/stdin)")
    create.add_argument("--username", required=True)
    create.add_argument("--display-name", required=True, dest="display_name")
    create.add_argument("--email", required=True)
    create.add_argument("--role", required=True, choices=_ROLE_VALUES)
    # Deliberately NO --password: the password is never a command-line argument.
    create.set_defaults(func=_cmd_create_user)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UserCreationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
