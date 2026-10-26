"""The real runner (task 28d / #221): an agent session fixes the defect.

Scaffold status
---------------
This replaces ``StubRunner``'s fake-client wiring with a real agent session,
but keeps the SDK *behind a seam* (``AgentSession``) so #221 is tested with a
**fake SDK** -- no key, no network, no SDK import in the test path. The real
Claude Agent SDK session is built lazily in ``build_default_session`` and is
only imported when the responder actually runs in ``RESPONDER_MODE=real`` on
the owner's host for the recorded drill (task 39). Importing this module does
**not** import the SDK, so ``test_mode_stub_imports_no_agent_sdk`` still holds.

What the session does is defined by ``prompt.SYSTEM_PROMPT``: investigate via
the API, reproduce with a failing test, make the smallest fix, open a pull
request on ``responder/<fingerprint>`` (never push to ``main``), or take the
US-15 false-positive path and change nothing.

Trust rule (unchanged from the stub): only ``state`` values and the validated
alert labels are used here. No advisory text, title, path or URL from the API
is read, logged, or passed to the agent as data it must act on.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .actlog import ActionLog
from .api_client import ApiError, ResponderApi
from .prompt import SYSTEM_PROMPT, build_task


@dataclass(frozen=True)
class AgentResult:
    """What a session reports back. ``model`` is the model the API actually served."""

    outcome: str  # "pull_request_opened" | "no_change" | "error"
    model: str
    pull_request: str | None = None
    explanation: str | None = None


class AgentSession(Protocol):
    """The seam the real SDK sits behind; a fake implements this in tests (#221)."""

    def run(self, system_prompt: str, task: str) -> AgentResult: ...


class RealRunner:
    """Woken per alert; starts one agent session that may open a fix PR.

    ``make_session`` is injected so tests pass a fake SDK. In production it is
    ``build_default_session`` (below), which wires the Claude Agent SDK.
    """

    def __init__(self, api: ResponderApi, log: ActionLog, model: str, make_session) -> None:
        self._api = api
        self._log = log
        self._model = model
        self._make_session = make_session

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
        session = self._make_session(self._model)
        try:
            result = session.run(SYSTEM_PROMPT, build_task(fingerprint, finding_id))
        except Exception:  # noqa: BLE001 - any session failure is a failed run
            return self._error(fingerprint, finding_id, "agent_session_failed")

        served = result.model or self._model
        if result.outcome == "pull_request_opened":
            log.emit("pull_request_opened", outcome="agent", fingerprint=fingerprint,
                     finding_id=finding_id, pull_request=result.pull_request, model=served)
            return "pull_request_opened"
        if result.outcome == "no_change":
            return self._no_change(fingerprint, finding_id,
                                   result.explanation or "The agent found no reproducible defect.",
                                   model=served)
        return self._error(fingerprint, finding_id, "agent_reported_error", model=served)

    def _no_change(self, fingerprint, finding_id, explanation, *, model=None) -> str:
        self._log.emit("no_change", outcome="no_change", fingerprint=fingerprint,
                       finding_id=finding_id, explanation=explanation, model=model or self._model)
        return "no_change"

    def _error(self, fingerprint, finding_id, reason, *, model=None) -> str:
        self._log.emit("run_failed", outcome="error", fingerprint=fingerprint,
                       finding_id=finding_id, reason=reason, model=model or self._model)
        return "error"


def build_default_session(model: str) -> AgentSession:
    """Wire the real Claude Agent SDK session (F2). Imported lazily on purpose.

    Not implemented in this scaffold: wiring the live SDK is the remaining part
    of #221, done on the owner's host with ANTHROPIC_API_KEY in the local .env
    (F2/F4). It must return an ``AgentResult`` whose ``model`` is the model the
    API reported serving the request, so the drill log shows what ran.
    """
    raise NotImplementedError(
        "the live Claude Agent SDK session is the remaining part of #221; it is wired on "
        "the owner's host with ANTHROPIC_API_KEY in the local .env (F2/F4). Tests use a fake session."
    )
