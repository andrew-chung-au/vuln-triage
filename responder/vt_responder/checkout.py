"""A fresh temporary checkout per run, deleted afterwards (task 28d / #221).

``fresh_checkout`` makes a new directory, asks the git seam to clone into it,
refuses to start unless the working tree is clean, and removes the directory
when the run ends, on success and on error alike.

``SubprocessGit`` is the real seam (``git clone`` / ``git status``). It is not
used by tests, which pass a fake. The token never goes on a command line or in
the remote URL: ``git_auth_env`` hands it to git through environment config.
"""

from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Protocol

from .envscrub import minimal_env


class CheckoutError(RuntimeError):
    """The checkout could not be made or did not start clean."""


class CheckoutGit(Protocol):
    def clone(self, dest: Path) -> None: ...
    def is_clean(self, dest: Path) -> bool: ...


@contextmanager
def fresh_checkout(git: CheckoutGit, *, parent: Path | None = None) -> Iterator[Path]:
    base = tempfile.mkdtemp(prefix="vt-responder-", dir=None if parent is None else str(parent))
    dest = Path(base) / "checkout"
    try:
        try:
            git.clone(dest)
            clean = git.is_clean(dest)
        except CheckoutError:
            raise
        except Exception as exc:  # noqa: BLE001 - never leak the underlying message (may carry a URL)
            raise CheckoutError(f"checkout failed ({type(exc).__name__})") from None
        if not clean:
            raise CheckoutError("checkout working tree is not clean")
        yield dest
    finally:
        shutil.rmtree(base, ignore_errors=True)


def git_auth_env(token: str) -> dict[str, str]:
    """Environment that lets git use ``token`` for github.com over HTTPS.

    VERIFY: GitHub accepts ``Authorization: Basic base64(x-access-token:<token>)``
    for git over HTTPS, and git reads ``GIT_CONFIG_COUNT/KEY_n/VALUE_n`` (git >= 2.31).
    """
    basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    return {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
        "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {basic}",
        "GIT_TERMINAL_PROMPT": "0",
    }


class SubprocessGit:
    """Real clone of ``https://github.com/<repo>.git``; not exercised by tests."""

    def __init__(self, repo: str, token: str) -> None:
        self._url = f"https://github.com/{repo}.git"
        self._token = token

    def _run(self, args: list[str], cwd: Path | None = None) -> str:
        import os

        # The runner's own git call: the git credential plus allowlisted names only.
        env = {**minimal_env(os.environ), **git_auth_env(self._token)}
        done = subprocess.run(["git", *args], cwd=cwd, env=env, check=False,
                              capture_output=True, text=True, timeout=300)
        if done.returncode != 0:
            raise CheckoutError(f"git {args[0]} failed")  # stderr may echo the URL: not included
        return done.stdout

    def clone(self, dest: Path) -> None:
        self._run(["clone", "--depth", "1", "--", self._url, str(dest)])

    def is_clean(self, dest: Path) -> bool:
        return self._run(["status", "--porcelain"], cwd=dest).strip() == ""
