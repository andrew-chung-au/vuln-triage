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
limit; an error, timeout or "no change" removes a remote branch only if this run
created it. The tool policy is a guardrail for a confused agent, not a sandbox
for a hostile one: see ``_docs/responder-security-limits.md``.

Two sessions sit behind the seam. ``sdk_session.SdkSession`` (``RESPONDER_RUNTIME=sdk``) opens the pull
request itself. ``cli_session.CliSession`` (``cli``, the default, #260) runs headless ``claude -p`` and
only commits locally: it reports ``fixed`` and THIS runner then stops the agent, has ``publisher`` check
the commits, push and open the pull request, and applies the same S4 read-back as for the SDK.

For the SDK runtime, what the session does is defined by ``prompt.SYSTEM_PROMPT``: investigate via
the API, reproduce with a failing test, make the smallest fix, open a pull
request on ``responder/<fingerprint>`` (never push to ``main``), or take the
US-15 false-positive path and change nothing.

Trust rule (unchanged from the stub): only ``state`` values and the validated
alert labels are used here. No advisory text, title, path or URL from the API
is read, logged, or passed to the agent as data it must act on.
"""

from __future__ import annotations

import os
import re
import threading
import time
import uuid
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from .actlog import ActionLog
from .api_client import ApiError, ResponderApi
from .checkout import CheckoutError, CheckoutGit, fresh_checkout
from .config import DEFAULT_MAX_BUDGET_USD, DEFAULT_MAX_TURNS, DEFAULT_RUN_TIMEOUT_SECONDS
from .envscrub import redact
from .github_client import BranchClient
from .installer import InstallError, Installer
from .policy import BRANCH_PREFIX, ToolPolicy
from .procs import kill_marked_processes
from .prompt import SYSTEM_PROMPT, build_task
from .publisher import GitPublisher, PublishError, Snapshot

_PR_NUMBER = re.compile(r"https://github\.com/[^/]+/[^/]+/pull/([0-9]+)")
MAX_FAILURE_TEXT = 500  # most agent text a run_failed line carries
MAX_DENIED_CALL_CHARS = 200  # each denied tool call in run_failed (at most 5 of them)
_UNKNOWN = object()  # the branch could not be inspected before the session: never delete it


@dataclass(frozen=True)
class AgentResult:
    """What a session reports back. ``model`` is the model the API actually served."""

    # "pull_request_opened" | "no_change" | "error", and (CLI runtime, #260) "fixed": the agent
    # committed locally and the runner must check, push and open the pull request itself.
    outcome: str
    model: str
    pull_request: str | None = None
    explanation: str | None = None
    reason: str | None = None  # a short machine code for a failed run (CLI runtime); safe to log
    # CLI runtime: the tool calls the CLI refused, as "Tool: <command or path>" windows of agent text
    # (at most 5). Untrusted: the runner redacts each, then cuts it to MAX_DENIED_CALL_CHARS.
    denied_calls: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunContext:
    """Everything a session needs for one alert; holds no secret."""

    fingerprint: str
    checkout: Path | None
    policy: ToolPolicy | None
    log: ActionLog
    max_turns: int
    timeout_seconds: int
    run_marker: str = ""  # tags every process of the run so the runner can stop them (procs.py)
    max_budget_usd: float = DEFAULT_MAX_BUDGET_USD


class _RunTimeout(Exception):
    """The session did not finish inside the run's time limit."""


def _call_with_timeout(fn: Callable[[], Any], timeout: float) -> Any:
    """Run ``fn`` on a daemon thread. A worker that never finishes is abandoned, and
    because it is a daemon thread it cannot keep the interpreter from exiting (#244 S3)."""
    box: dict[str, Any] = {}
    done = threading.Event()

    def target() -> None:
        try:
            box["value"] = fn()
        except BaseException as exc:  # noqa: BLE001 - handed to the caller
            box["error"] = exc
        finally:
            done.set()

    threading.Thread(target=target, name="responder-session", daemon=True).start()
    if not done.wait(timeout):
        raise _RunTimeout()
    if "error" in box:
        raise box["error"]
    return box["value"]


class AgentSession(Protocol):
    """The seam the real SDK sits behind; a fake implements this in tests (#221)."""

    def run(self, system_prompt: str, task: str) -> AgentResult: ...


class RealRunner:
    """Woken per alert; starts one agent session that may open a fix PR.

    ``make_session(model, ctx)`` is injected so tests pass a fake SDK. In
    production it builds ``sdk_session.SdkSession`` through ``build_default_session``.
    With ``git`` set, each run gets a fresh temporary checkout that is deleted
    afterwards (also on error). The run is bounded by ``timeout_seconds``; any
    session error or timeout is a failed run (``error``). A failed or no-change
    run deletes a ``responder/<fingerprint>`` branch only if THIS run created it
    (absent before the session, or its SHA changed); a branch that existed and is
    unchanged is kept and logged as ``branch_preserved`` (#244 S1). The agent's
    processes are stopped before the checkout is removed and the branch deleted.
    """

    def __init__(self, api: ResponderApi, log: ActionLog, model: str, make_session, *,
                 git: CheckoutGit | None = None, branches: BranchClient | None = None,
                 max_turns: int = DEFAULT_MAX_TURNS,
                 timeout_seconds: int = DEFAULT_RUN_TIMEOUT_SECONDS,
                 timeout_grace_seconds: float = 5.0, repo: str | None = None,
                 installer: Installer | None = None, secrets: Sequence[str] = (),
                 max_budget_usd: float = DEFAULT_MAX_BUDGET_USD,
                 kill_agent: Callable[[str], Any] = kill_marked_processes,
                 publisher: GitPublisher | None = None, system_prompt: str = SYSTEM_PROMPT,
                 task_builder: Callable[[str, str | None], str] = build_task) -> None:
        self._api = api
        # CLI runtime (#260): with a publisher, a session may report ``fixed`` (committed locally);
        # the runner then checks the commits, pushes and opens the pull request itself.
        self._publisher = publisher
        self._system_prompt = system_prompt
        self._task_builder = task_builder
        # When set, a reported pull request must be a PR URL in this repository, and
        # (with a branch client) the pull request itself must be this run's (#244 S4).
        self._repo = repo
        self._pr_url = (
            re.compile(rf"https://github\.com/{re.escape(repo)}/pull/[0-9]+", re.IGNORECASE)
            if repo else None
        )
        self._installer = installer
        self._secrets = tuple(s for s in secrets if s)
        self._budget = max_budget_usd
        self._kill_agent = kill_agent
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

        # A failed job exists: hand the task to the agent session. First record whether
        # responder/<fp> already exists and where it points (S1), so cleanup only ever
        # removes what this run created.
        before = self._snapshot_branch(fingerprint, finding_id)
        result, failure = self._run_session(fingerprint, finding_id)
        if result is None:
            return self._finish_failed(fingerprint, finding_id, failure or "agent_session_failed",
                                       before=before)

        served = result.model or self._model
        if result.outcome == "pull_request_opened" and result.pull_request:
            if self._pr_url and not self._pr_url.fullmatch(result.pull_request):
                return self._finish_failed(fingerprint, finding_id, "pull_request_url_invalid",
                                           model=served, before=before)
            problem = self._check_pull_request(fingerprint, result.pull_request)
            if problem:
                return self._finish_failed(fingerprint, finding_id, problem, model=served, before=before)
            log.emit("pull_request_opened", outcome="agent", fingerprint=fingerprint,
                     finding_id=finding_id, pull_request=redact(result.pull_request, self._secrets),
                     model=served)
            return "pull_request_opened"
        if result.outcome == "no_change":
            # US-15: no change plus an explanation, and no branch this run created.
            self._cleanup_branch(fingerprint, finding_id, before)
            return self._no_change(fingerprint, finding_id,
                                   result.explanation or "The agent found no reproducible defect.",
                                   model=served)
        return self._finish_failed(fingerprint, finding_id, result.reason or "agent_reported_error",
                                   model=served, before=before, explanation=result.explanation,
                                   denied_calls=result.denied_calls)

    def _check_pull_request(self, fingerprint: str, url: str) -> str | None:
        """S4: the reported PR must be a pull request of this run. Returns a failure reason or None."""
        if not self._repo or self._branches is None:
            return None  # not configured to verify (tests and stub-like wiring)
        found = _PR_NUMBER.fullmatch(url)
        if not found:
            return "pull_request_url_invalid"
        try:
            pull = self._branches.get_pull_request(int(found.group(1)))
        except Exception:  # noqa: BLE001
            return "pull_request_unreadable"
        if not isinstance(pull, dict):
            return "pull_request_unreadable"
        head = pull.get("head") if isinstance(pull.get("head"), dict) else {}
        head_repo = head.get("repo") if isinstance(head.get("repo"), dict) else {}
        same_repo = str(head_repo.get("full_name", "")).lower() == self._repo.lower()
        if head.get("ref") != BRANCH_PREFIX + fingerprint or not same_repo:
            return "pull_request_not_this_runs"
        return None

    def _run_session(self, fingerprint: str, finding_id: str | None):
        """Run one bounded session in a fresh checkout. Returns ``(result, failure_reason)``.

        Order on every exit (S3): stop the agent's processes, then the checkout is
        removed (leaving the ``with``), then the caller deletes the branch.
        """
        marker = uuid.uuid4().hex
        deadline = time.monotonic() + self._timeout
        try:
            cm = fresh_checkout(self._git) if self._git is not None else nullcontext(None)
            with cm as path:
                remaining = self._timeout
                if path is not None and self._installer is not None:
                    # S2: clone -> install -> session. The runner installs, with no secret in
                    # the environment; the install counts against the run's time limit.
                    self._installer.install(path, timeout=self._timeout)
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return None, "agent_timeout"
                # The cloned head and .git/config, recorded before the agent can touch either (#260).
                snapshot = (self._publisher.snapshot(path)
                            if path is not None and self._publisher is not None else None)
                policy = ToolPolicy(path, fingerprint) if path is not None else None
                ctx = RunContext(fingerprint, path, policy, self._log, self._max_turns, remaining,
                                 run_marker=marker, max_budget_usd=self._budget)
                session = self._make_session(self._model, ctx)
                try:
                    result = _call_with_timeout(
                        lambda: session.run(self._system_prompt, self._task_builder(fingerprint, finding_id)),
                        remaining + self._grace)
                finally:
                    self._stop_agent(marker, fingerprint, finding_id)
                if result.outcome == "fixed":
                    # The agent is stopped; now the runner's own checks, push and pull request.
                    result = self._publish(path, snapshot, fingerprint, finding_id, result)
                return result, None
        except CheckoutError:
            return None, "checkout_failed"
        except InstallError:
            return None, "install_failed"
        except PublishError as exc:
            return None, exc.reason
        except (_RunTimeout, TimeoutError):
            return None, "agent_timeout"
        except Exception as exc:  # noqa: BLE001 - any session failure is a failed run
            return None, f"agent_session_failed:{type(exc).__name__}"

    def _publish(self, path: Path | None, snapshot: Snapshot | None, fingerprint: str,
                 finding_id: str | None, result: AgentResult) -> AgentResult:
        if self._publisher is None or path is None or snapshot is None:
            raise PublishError("publisher_missing")
        url = self._publisher.publish(path, snapshot, fingerprint, finding_id, result.explanation)
        self._log.emit("branch_pushed", outcome="ok", fingerprint=fingerprint, finding_id=finding_id,
                       branch=BRANCH_PREFIX + fingerprint)
        return AgentResult("pull_request_opened", result.model, pull_request=url)

    def _stop_agent(self, marker: str, fingerprint: str, finding_id: str | None) -> None:
        try:
            self._kill_agent(marker)
        except Exception:  # noqa: BLE001 - a failed kill must not stop the cleanup after it
            self._log.emit("agent_kill_failed", outcome="error", fingerprint=fingerprint,
                           finding_id=finding_id)

    def _snapshot_branch(self, fingerprint: str, finding_id: str | None):
        """The head SHA of ``responder/<fp>`` now, ``None`` if absent, ``_UNKNOWN`` if unreadable."""
        if self._branches is None:
            return None
        try:
            return self._branches.get_branch_sha(BRANCH_PREFIX + fingerprint)
        except Exception:  # noqa: BLE001
            return _UNKNOWN

    def _cleanup_branch(self, fingerprint: str, finding_id: str | None, before: Any = None) -> None:
        """Delete ``responder/<fp>`` only if this run created it: it was absent before the
        session, or its head SHA changed. Otherwise leave it and log ``branch_preserved``."""
        if self._branches is None:
            return
        branch = BRANCH_PREFIX + fingerprint
        try:
            if before is _UNKNOWN:
                self._preserved(fingerprint, finding_id, branch, "not_inspectable_before_run")
                return
            now = self._branches.get_branch_sha(branch)
            if now is None:
                return  # nothing there
            if before is not None and now == before:
                self._preserved(fingerprint, finding_id, branch, "existed_before_run_unchanged")
                return
            deleted = self._branches.delete_branch_if_exists(branch)
        except Exception:  # noqa: BLE001
            self._log.emit("branch_cleanup_failed", outcome="error", fingerprint=fingerprint,
                           finding_id=finding_id, branch=branch)
            return
        if deleted:
            self._log.emit("branch_deleted", outcome="ok", fingerprint=fingerprint,
                           finding_id=finding_id, branch=branch)

    def _preserved(self, fingerprint, finding_id, branch, reason) -> None:
        self._log.emit("branch_preserved", outcome="kept", fingerprint=fingerprint,
                       finding_id=finding_id, branch=branch, reason=reason)

    def _finish_failed(self, fingerprint, finding_id, reason, *, model=None, before: Any = None,
                       explanation: str | None = None, denied_calls: Sequence[str] = ()) -> str:
        self._cleanup_branch(fingerprint, finding_id, before)
        return self._error(fingerprint, finding_id, reason, model=model, explanation=explanation,
                           denied_calls=denied_calls)

    def _no_change(self, fingerprint, finding_id, explanation, *, model=None) -> str:
        # redact the whole text, then cut: the session hands over up to 800 characters
        shown = (redact(explanation, self._secrets) or "")[:MAX_FAILURE_TEXT].strip()
        self._log.emit("no_change", outcome="no_change", fingerprint=fingerprint,
                       finding_id=finding_id, explanation=shown,
                       model=model or self._model)
        return "no_change"

    def _error(self, fingerprint, finding_id, reason, *, model=None, explanation: str | None = None,
               denied_calls: Sequence[str] = ()) -> str:
        extra: dict[str, Any] = {}
        # Each refused tool call: redact the whole window, then cut it (same order as the explanation).
        denied = [(redact(call, self._secrets) or "")[:MAX_DENIED_CALL_CHARS].strip() for call in denied_calls[:5]]
        denied = [call for call in denied if call]
        if denied:
            extra["denied_calls"] = denied
        if explanation:
            # Untrusted agent text: redact the WHOLE window first, then cut (a secret straddling the cut
            # must not survive as a fragment). The RESULT: line text keeps its start, a final-message tail its end.
            whole = redact(explanation, self._secrets) or ""
            shown = (whole[:MAX_FAILURE_TEXT] if reason == "agent_escalated"
                     else whole[-MAX_FAILURE_TEXT:]).strip()
            if shown:
                extra["explanation"] = shown
        self._log.emit("run_failed", outcome="error", fingerprint=fingerprint,
                       finding_id=finding_id, reason=reason, model=model or self._model, **extra)
        return "error"


def build_default_session(model: str, ctx: RunContext, *, api_key: str, github_token: str,
                          env: Mapping[str, str] | None = None, sdk: Any = None,
                          secrets: Sequence[str] = ()) -> AgentSession:
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

    return SdkSession(model, ctx, api_key=api_key, github_token=github_token, sdk=sdk, secrets=secrets)
