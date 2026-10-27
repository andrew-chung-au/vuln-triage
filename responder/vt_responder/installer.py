"""Install the project's test dependencies into the fresh checkout (#244 S2).

The checkout is a bare shallow clone, so ``make backend-test`` stops with
"backend/.venv is missing". The agent is denied ``make install``, ``uv``, ``npm``
and ``pytest`` (policy), so the runner installs before the agent starts:
``clone -> install -> session``. The install runs with an environment that holds
only allowlisted names (no model key, no token), in its own process group so a
timeout stops ``make`` and the ``npm``/``uv`` it started, and its output is
discarded (it is not read, logged or shown to anyone).

VERIFY (not run live): ``make install`` needs ``uv``, ``node`` and ``npm`` on the
responder host and network to the PyPI and npm registries; it runs ``npm ci``
(frontend), ``uv sync --locked`` (backend, responder). How long it takes is
unknown until the first live run; it counts against the run's time limit.
Dependency install scripts run with the responder's user and no secrets in the
environment, but with network.
"""

from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from .envscrub import minimal_env


class InstallError(RuntimeError):
    """The dependencies could not be installed; the message never carries output."""


class Installer(Protocol):
    def install(self, checkout: Path, *, timeout: float) -> None: ...


class SubprocessInstaller:
    def __init__(self, command: Sequence[str] = ("make", "install"), *,
                 environ: Mapping[str, str] | None = None) -> None:
        self._command = list(command)
        self._environ = environ

    def install(self, checkout: Path, *, timeout: float) -> None:
        env = minimal_env(os.environ if self._environ is None else self._environ)
        try:
            proc = subprocess.Popen(self._command, cwd=checkout, env=env, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    start_new_session=True)
        except OSError:
            raise InstallError("install could not start") from None
        try:
            code = proc.wait(timeout=max(timeout, 0.1))
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)  # its own group (start_new_session), never ours
            except OSError:
                pass
            proc.wait()
            raise InstallError("install timed out") from None
        if code != 0:
            raise InstallError("install failed")
