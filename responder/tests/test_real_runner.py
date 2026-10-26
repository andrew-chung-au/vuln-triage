"""#221 real runner, exercised with a FAKE agent session (no SDK, no key, no network).

The fake session records the prompt and task it is handed and returns a
scripted ``AgentResult``. These tests prove the runner's decision flow and the
no-advisory-text / model-logging guarantees without the Claude Agent SDK.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from vt_responder.actlog import ActionLog
from vt_responder.api_client import ResponderApi
from vt_responder.real_runner import AgentResult, RealRunner

from conftest import ADVISORY_TEXT, FakeBackend

pytestmark = pytest.mark.unit

MODEL = "claude-sonnet-5-5"


class FakeSession:
    """A stand-in for the SDK session; scripts an outcome and records the call."""

    def __init__(self, result: AgentResult) -> None:
        self._result = result
        self.seen: list[tuple[str, str]] = []

    def run(self, system_prompt: str, task: str) -> AgentResult:
        self.seen.append((system_prompt, task))
        return self._result


def make_runner(tmp_path: Path, result: AgentResult):
    backend = FakeBackend()
    api = ResponderApi("http://backend.test", "tok", transport=httpx.MockTransport(backend.handler))
    lines: list[str] = []
    session = FakeSession(result)
    runner = RealRunner(api, ActionLog(lines.append), MODEL, make_session=lambda m: session)
    return runner, backend, lines, session


def records(lines):
    import json
    return [json.loads(line) for line in lines]


def test_failed_job_runs_the_agent_and_logs_the_served_model(tmp_path: Path):
    runner, backend, lines, session = make_runner(
        tmp_path, AgentResult(outcome="pull_request_opened", model=MODEL, pull_request="https://pr/1")
    )
    backend.add_finding("42", ["failed"])

    assert runner.run("fp1", "42") == "pull_request_opened"
    # The agent was handed the finding and the static system prompt.
    assert session.seen and "42" in session.seen[0][1]
    pr = [r for r in records(lines) if r["event"] == "pull_request_opened"][0]
    assert pr["pull_request"] == "https://pr/1"
    assert pr["model"] == MODEL


def test_no_failed_job_is_a_false_positive_without_calling_the_agent(tmp_path: Path):
    runner, backend, lines, session = make_runner(
        tmp_path, AgentResult(outcome="pull_request_opened", model=MODEL)
    )
    backend.add_finding("42", ["sent"])

    assert runner.run("fp1", "42") == "no_change"
    assert session.seen == []  # no model call for an obvious false positive


def test_unknown_finding_is_no_change(tmp_path: Path):
    runner, backend, lines, session = make_runner(tmp_path, AgentResult(outcome="no_change", model=MODEL))
    assert runner.run("fp1", "999") == "no_change"
    assert session.seen == []


def test_agent_no_change_explanation_is_logged(tmp_path: Path):
    runner, backend, lines, _ = make_runner(
        tmp_path, AgentResult(outcome="no_change", model=MODEL, explanation="checked: not reproducible")
    )
    backend.add_finding("42", ["failed"])
    assert runner.run("fp1", "42") == "no_change"
    nc = [r for r in records(lines) if r["event"] == "no_change"][0]
    assert nc["explanation"] == "checked: not reproducible"


def test_session_exception_is_a_failed_run(tmp_path: Path):
    class Boom:
        def run(self, system_prompt, task):
            raise RuntimeError("sdk blew up")

    backend = FakeBackend()
    api = ResponderApi("http://backend.test", "tok", transport=httpx.MockTransport(backend.handler))
    lines: list[str] = []
    runner = RealRunner(api, ActionLog(lines.append), MODEL, make_session=lambda m: Boom())
    backend.add_finding("42", ["failed"])
    assert runner.run("fp1", "42") == "error"


def test_no_advisory_text_or_secret_reaches_the_log(tmp_path: Path):
    # The fake backend plants ADVISORY_TEXT in the finding title; it must not leak.
    runner, backend, lines, _ = make_runner(
        tmp_path, AgentResult(outcome="pull_request_opened", model=MODEL, pull_request="https://pr/1")
    )
    backend.add_finding("42", ["failed"])
    runner.run("fp1", "42")
    blob = "\n".join(lines)
    assert ADVISORY_TEXT not in blob
