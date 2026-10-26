"""The real runner (task 28d / #221): an agent session fixes the defect.

Status
------
The SDK sits *behind a seam* (``AgentSession``) so #221 is tested with a
**fake SDK** -- no key, no network, no SDK import in the test path. The live
session is ``sdk_session.SdkSession`` (built by ``build_default_session``,
which refuses in CI/test and without the key and token); it has never been run
live from this repository's tests and is first exercised on the owner's host for
the recorded drill (task 39). Importing this module does **not** import the
SDK, so ``test_mode_stub_imports_no_agent_sdk`` still holds.

Per alert: a fresh temporary checkout (``checkout.py``), a ``ToolPolicy`` for
``responder/<fingerprint>`` (``policy.py``), a turn limit and a wall-clock
limit; an error, timeout or "no change" leaves no remote branch.

What the session does is defined by ``prompt.SYSTEM_PROMPT``: investigate via
the API, reproduce with a failing test, make the smallest fix, open a pull
request on ``responder/<fingerprint>`` (never push to ``main``), or take the
US-15 false-positive path and change nothing.

Trust rule (unchanged from the stub): only ``state`` values and the validated
alert labels are used here. No advisory text, title, path or URL from the API
is read, logged, or passed to the agent as data it must act on.
"""

from __future__ import annotations

import concurrent.futures
import os
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from .actlog import ActionLog
from .api_client import ApiError, ResponderApi
from .checkout import CheckoutError, CheckoutGit, fresh_checkout
from .config import DEFAULT_MAX_TURNS, DEFAULT_RUN_TIMEOUT_SECONDS
from .github_client import BranchClient
from .policy import BRANCH_PREFIX, ToolPolicy
from .prompt import SYSTEM_PROMPT, build_task


@dataclass(frozen=True)
class AgentResult:
    """What a session reports back. ``model`` is the model the API actually served."""

    outcome: str  # "pull_request_opened" | "no_change" | "error"
    model: str
    pull_request: str | None = None
    explanation: str | None = None


@dataclass(frozen=True)
class RunContext:
    """Everything a session needs for one alert; holds no secret."""

    fingerprint: str
    checkout: Path | None
    policy: ToolPolicy | None
    log: ActionLog
    max_turns: int
    timeout_seconds: int


class AgentSession(Protocol):
    """The seam the real SDK sits behind; a fake implements this in tests (#221)."""

    def run(self, system_prompt: str, task: str) -> AgentResult: ...


class RealRunner:
    """Woken per alert; starts one agent session that may open a fix PR.

    ``make_session(model, ctx)`` is injected so tests pass a fake SDK. In
    production it builds ``sdk_session.SdkSession`` through ``build_default_session``.
    With ``git`` set, each run gets a fresh temporary checkout that is deleted
    afterwards (also on error). The run is bounded by ``timeout_seconds``; any
    session error or timeout is a failed run (``error``), and a failed or
    no-change run never leaves a ``responder/<fingerprint>`` branch behind.
    """

    def __init__(self, api: ResponderApi, log: ActionLog, model: str, make_session, *,
                 git: CheckoutGit | None = None, branches: BranchClient | None = None,
                 max_turns: int = DEFAULT_MAX_TURNS,
                 timeout_seconds: int = DEFAULT_RUN_TIMEOUT_SECONDS,
                 timeout_grace_seconds: float = 5.0) -> None:
        self._api = api
        self._log = log
        self._model = model
        self._make_session = make_session
        self._git = git
        self._branches = branches
        self._max_turns = max_turns
        self._timeout = timeout_seconds
        self._grace = timeout_grace_seconds

    def run(self, fingerprint: str, finding_id: str | None) -> str:
        log = self._log
        log.emit("run_started", outcome="started", fingerprint=fingerprint,
                 finding_id=finding_id, model=self._model)

        # Cheap, deterministic pre-checks mirror the stub so an obvious
        # false positive never spends a model call.
        if not finding_id:
            return self._no_change(
                fingerprint, finding_id,
                "No finding_id on the alert, so this is a Grafana test or NoData alert, "
                "not an undelivered finding.",
            )
        try:
            self._api.get_finding(finding_id)
        except ApiError as exc:
            if exc.status == 404:
                return self._no_change(fingerprint, finding_id,
                                       "The finding id is unknown (404); there is no defect to reproduce.")
            return self._error(fingerprint, finding_id, "api_get_finding_failed")
        try:
            jobs = self._api.list_jobs(finding_id)
        except ApiError:
            return self._error(fingerprint, finding_id, "api_list_jobs_failed")
        states = sorted({str(job.get("state")) for job in jobs if isinstance(job, dict)})
        log.emit("api_read", outcome="ok", fingerprint=fingerprint, finding_id=finding_id,
                 job_states=states)
        if "failed" not in states:
            return self._no_change(
                fingerprint, finding_id,
                "No notification job is in state failed (states: " + (", ".join(states) or "none")
                + "), so there is no defect to reproduce.",
            )

        # A failed job exists: hand the task to the agent session.
        result, failure = self._run_session(fingerprint, finding_id)
        if result is None:
            return self._finish_failed(fingerprint, finding_id, failure or "agent_session_failed")

        served = result.model or self._model
        if result.outcome == "pull_request_opened" and result.pull_request:
            log.emit("pull_request_opened", outcome="agent", fingerprint=fingerprint,
                     finding_id=finding_id, pull_request=result.pull_request, model=served)
            return "pull_request_opened"
        if result.outcome == "no_change":
            # US-15: no change plus an explanation, and no branch even if one was pushed.
            self._cleanup_branch(fingerprint, finding_id)
            return self._no_change(fingerprint, finding_id,
                                   result.explanation or "The agent found no reproducible defect.",
                                   model=served)
        return self._finish_failed(fingerprint, finding_id, "agent_reported_error", model=served)

    def _run_session(self, fingerprint: str, finding_id: str | None):
        """Run one bounded session in a fresh checkout. Returns ``(result, failure_reason)``."""
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            cm = fresh_checkout(self._git) if self._git is not None else nullcontext(None)
            with cm as path:
                policy = ToolPolicy(path, fingerprint) if path is not None else None
                ctx = RunContext(fingerprint, path, policy, self._log, self._max_turns, self._timeout)
                session = self._make_session(self._model, ctx)
                future = pool.submit(session.run, SYSTEM_PROMPT, build_task(fingerprint, finding_id))
                try:
                    return future.result(timeout=self._timeout + self._grace), None
                except concurrent.futures.TimeoutError:
                    return None, "agent_timeout"
        except CheckoutError:
            return None, "checkout_failed"
        except Exception:  # noqa: BLE001 - any session failure is a failed run
            return None, "agent_session_failed"
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    def _cleanup_branch(self, fingerprint: str, finding_id: str | None) -> None:
        """Delete ``responder/<fingerprint>`` on the remote if the run created it."""
        if self._branches is None:
            return
        branch = BRANCH_PREFIX + fingerprint
        try:
            deleted = self._branches.delete_branch_if_exists(branch)
        except Exception:  # noqa: BLE001
            self._log.emit("branch_cleanup_failed", outcome="error", fingerprint=fingerprint,
                           finding_id=finding_id, branch=branch)
            return
        if deleted:
            self._log.emit("branch_deleted", outcome="ok", fingerprint=fingerprint,
                           finding_id=finding_id, branch=branch)

    def _finish_failed(self, fingerprint, finding_id, reason, *, model=None) -> str:
        self._cleanup_branch(fingerprint, finding_id)
        return self._error(fingerprint, finding_id, reason, model=model)

    def _no_change(self, fingerprint, finding_id, explanation, *, model=None) -> str:
        self._log.emit("no_change", outcome="no_change", fingerprint=fingerprint,
                       finding_id=finding_id, explanation=explanation, model=model or self._model)
        return "no_change"

    def _error(self, fingerprint, finding_id, reason, *, model=None) -> str:
        self._log.emit("run_failed", outcome="error", fingerprint=fingerprint,
                       finding_id=finding_id, reason=reason, model=model or self._model)
        return "error"


def build_default_session(model: str, ctx: RunContext, *, api_key: str, github_token: str,
                          env: Mapping[str, str] | None = None, sdk: Any = None) -> AgentSession:
    """Build the real Claude Agent SDK session (F2). The SDK is imported lazily, inside.

    Refused (``ConfigError``) in a CI or test environment and when the API key or
    the GitHub token is missing, so a live call can never start from a test run.
    ``env`` and ``sdk`` exist only so tests can exercise this with a fake SDK.
    """
    from .config import ConfigError, _in_test_or_ci

    if _in_test_or_ci(os.environ if env is None else env):
        raise ConfigError("the live agent session is refused in test and CI")
    if not api_key or not github_token:
        raise ConfigError("ANTHROPIC_API_KEY and RESPONDER_GITHUB_TOKEN are required for a live session")
    from .sdk_session import SdkSession

    return SdkSession(model, ctx, api_key=api_key, github_token=github_token, sdk=sdk)
