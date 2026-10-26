"""Static, offline checks for the P-DEMO-BE helpers and wiring (#233).

These run in ``make test`` / ``make verify`` (no Docker). The container case itself is
``tests/test_compose_demo_be.py`` and runs only under ``make test-compose JOB=responder``.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
from typing import Any

import pytest

import compose_alert
import compose_responder

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_SCRIPT = _ROOT / "ci" / "test-compose.sh"
_CASE = _ROOT / "tests" / "test_compose_demo_be.py"


def _fake_run(calls: list[dict[str, Any]], returncode: int = 0):  # type: ignore[no-untyped-def]
    def run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append({"cmd": list(cmd), **kwargs})
        return subprocess.CompletedProcess(cmd, returncode, stdout="", stderr="boom")

    return run


def test_recreate_backend_unset_removes_the_defect_and_force_recreates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VT_DEMO_DEFECT", "notify_no_fix")  # the caller's environment must not leak through
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(compose_responder.subprocess, "run", _fake_run(calls))
    compose_responder.recreate_backend(None)
    (call,) = calls
    assert "VT_DEMO_DEFECT" not in call["env"]
    cmd = call["cmd"]
    for word in ("up", "-d", "--force-recreate", "--no-deps", "--wait", "backend"):
        assert word in cmd
    assert "restart" not in cmd  # restart does not re-read the environment


def test_recreate_backend_with_a_defect_sets_only_that_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VT_DEMO_DEFECT", raising=False)
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(compose_responder.subprocess, "run", _fake_run(calls))
    compose_responder.recreate_backend("notify_no_fix")
    assert calls[0]["env"]["VT_DEMO_DEFECT"] == "notify_no_fix"


def test_recreate_backend_failure_is_a_hard_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(compose_responder.subprocess, "run", _fake_run([], returncode=1))
    with pytest.raises(compose_responder.ComposeQueryError):
        compose_responder.recreate_backend(None)


def test_message_subject_reads_the_first_subject_header() -> None:
    message = {"Content": {"Headers": {"Subject": ["[FIRING:1] Top-tier owner notification overdue"]}}}
    assert compose_responder.message_subject(message) == "[FIRING:1] Top-tier owner notification overdue"
    assert compose_responder.message_subject({}) == ""
    assert compose_responder.message_subject({"Content": {"Headers": {}}}) == ""


def test_set_job_state_calls_alert_set_for_an_existing_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []

    def run_seam(args: list[str]) -> dict[str, Any]:
        seen.append(args)
        return {"updated": 1}

    monkeypatch.setattr(compose_alert, "run_seam", run_seam)
    assert compose_alert.set_job_state(42, "failed") == {"updated": 1}
    assert seen == [["alert-set", "--finding-id", "42", "--state", "failed"]]
    compose_alert.set_job_state("7", "failed", age_minutes=31)
    assert seen[-1] == ["alert-set", "--finding-id", "7", "--state", "failed", "--age-minutes", "31"]


def test_script_seeds_the_user_and_runs_the_demo_case_after_the_wiring_cases() -> None:
    text = _SCRIPT.read_text(encoding="utf-8")
    body = text[text.index("run_responder() {") : text.index('case "$JOB" in')]
    assert "seed_user || return 1" in body
    assert re.search(r"tests/test_compose_responder\.py\s+tests/test_compose_demo_be\.py", body)
    # The user the case logs in as is exported at the top of the script.
    for name in ("VT_TEST_USERNAME", "VT_TEST_PASSWORD", "VT_BACKEND_URL"):
        assert f'export {name}="' in text.split("run_telemetry()")[0]


def test_script_is_still_valid_bash() -> None:
    result = subprocess.run(["bash", "-n", str(_SCRIPT)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_the_case_is_compose_marked_states_its_limits_and_never_restarts_the_backend() -> None:
    text = _CASE.read_text(encoding="utf-8")
    # Built from parts so this unit module does not itself carry the marker text
    # (the marker-hygiene guard scans every test module for it).
    assert "pytestmark = pytest.mark." + "compose" in text
    flat = " ".join(text.split())
    assert "proves the WIRING only" in flat
    assert "applied BY THE HARNESS" in flat
    assert "WRITTEN WITHOUT BEING RUN" in flat
    assert '"restart"' not in text
