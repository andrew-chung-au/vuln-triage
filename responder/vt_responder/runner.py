"""The stub run: one deterministic pass per alert, no model, no SDK.

It proves the wiring only (architecture, Responder agent; testing.md section
Responder). The real runner (Claude Agent SDK) is task 28d (#221).

Decision rule:
- no ``finding_id`` (a Grafana test alert or the NoData alert): "no change";
- the finding is unknown (404): "no change";
- no notification job of the finding is ``failed``: "no change";
- otherwise a reproducible defect is assumed: branch ``responder/<fingerprint>``,
  the intended test and fix files, and a pull-request-opened event against
  the fake GitHub client. Nothing is pushed.

Everything read from the API is treated as data. Only ``state`` values are
consulted; no advisory text, path or URL from the API is used or logged.
"""

from __future__ import annotations

from typing import Protocol

from .actlog import ActionLog
from .api_client import ApiError, ResponderApi

# Intended files for the demo defect (US-15 example: no fixed version).
# VERIFY: the owner-notification formatter lives in backend/vulntriage/mail/message.py.
INTENDED_TEST_FILE = "tests/test_notify_no_fixed_version.py"
INTENDED_FIX_FILE = "backend/vulntriage/mail/message.py"


class GitClient(Protocol):
    def create_branch(self, name: str) -> None: ...
    def commit(self, branch: str, files: list[str], message: str) -> None: ...
    def push(self, branch: str) -> None: ...


class GitHubClient(Protocol):
    def open_pull_request(self, branch: str, title: str, body: str) -> str: ...


class StubRunner:
    def __init__(self, api: ResponderApi, git: GitClient, github: GitHubClient, log: ActionLog) -> None:
        self._api = api
        self._git = git
        self._github = github
        self._log = log

    def run(self, fingerprint: str, finding_id: str | None) -> str:
        """Run once. Returns ``no_change``, ``pull_request_opened`` or ``error``."""
        log = self._log
        log.emit("run_started", outcome="started", fingerprint=fingerprint, finding_id=finding_id)

        if not finding_id:
            return self._no_change(
                fingerprint, finding_id,
                "Checked the alert labels: no finding_id is present, so this is a Grafana test alert "
                "or the NoData alert, not an undelivered finding. No finding or job was read, so there "
                "is no defect to reproduce.",
            )

        try:
            self._api.get_finding(finding_id)
        except ApiError as exc:
            if exc.status == 404:
                return self._no_change(
                    fingerprint, finding_id,
                    "Checked the finding through the API: the finding id is unknown (404), so there is "
                    "no notification path to reproduce a defect in.",
                )
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
                f"Checked the finding and its {len(jobs)} notification job(s) through the API: none is in "
                "state failed (states seen: " + (", ".join(states) or "none") + "), so the notification "
                "path shows no defect to reproduce.",
            )

        branch = f"responder/{fingerprint}"
        files = [INTENDED_TEST_FILE, INTENDED_FIX_FILE]
        self._git.create_branch(branch)
        log.emit("branch_recorded", outcome="ok", fingerprint=fingerprint, finding_id=finding_id,
                 branch=branch, test_file=INTENDED_TEST_FILE, fix_file=INTENDED_FIX_FILE)
        self._git.commit(branch, files, f"Fix notification failure for finding {finding_id} (stub)")
        pr = self._github.open_pull_request(
            branch,
            f"Fix failed owner notification for finding {finding_id}",
            f"Stub run for alert {fingerprint}. Adds {INTENDED_TEST_FILE}; fixes {INTENDED_FIX_FILE}.",
        )
        log.emit("pull_request_opened", outcome="stub", fingerprint=fingerprint, finding_id=finding_id,
                 branch=branch, pull_request=pr)
        return "pull_request_opened"

    def _no_change(self, fingerprint: str, finding_id: str | None, explanation: str) -> str:
        self._log.emit("no_change", outcome="no_change", fingerprint=fingerprint,
                       finding_id=finding_id, explanation=explanation)
        return "no_change"

    def _error(self, fingerprint: str, finding_id: str | None, reason: str) -> str:
        self._log.emit("run_failed", outcome="error", fingerprint=fingerprint,
                       finding_id=finding_id, reason=reason)
        return "error"
