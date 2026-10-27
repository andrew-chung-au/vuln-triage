"""#241: real mode runs the agent in the background, with a retry cap and a concurrency cap.

Everything uses a fake session (no SDK, no key, no network). A "blocking" session
holds a run in flight until the test releases it, so the cases can look at the app
while a run is open.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from conftest import WEBHOOK_SECRET, FakeBackend, alert_body, make_settings
from test_real_runner_isolation import FakeCheckoutGit
from vt_responder.actlog import ActionLog
from vt_responder.api_client import ResponderApi
from vt_responder.app import create_app
from vt_responder.config import ConfigError, Settings
from vt_responder.fakes import FakeBranchClient
from vt_responder.guard import FingerprintGuard
from vt_responder.real_runner import AgentResult

pytestmark = pytest.mark.unit

URL = "/webhook/grafana"
HEADERS = {"Authorization": f"Bearer {WEBHOOK_SECRET}"}
MODEL = "claude-sonnet-5-5"
PR = "https://github.com/owner/repo/pull/1"
OK = AgentResult("pull_request_opened", MODEL, pull_request=PR)


class Script:
    """A fake session factory: each session runs ``behaviour(script, fingerprint)``."""

    def __init__(self, behaviour=None) -> None:
        self.behaviour = behaviour or (lambda s, fp: OK)
        self.started: list[str] = []
        self.entered = threading.Event()
        self.release = threading.Event()
        self.branches = None

    def block(self, s, fp):
        self.entered.set()
        assert self.release.wait(10), "test never released the run"
        return OK

    def make(self, model, ctx):
        script = self
        if script.branches is not None:
            script.branches.ref = "responder/" + ctx.fingerprint  # the PR "opened" is this run's (#244 S4)

        class Session:
            def run(self, system_prompt, task):
                script.started.append(ctx.fingerprint)
                return script.behaviour(script, ctx.fingerprint)

        return Session()


@dataclass
class Rig:
    app: object
    client: TestClient
    script: Script
    lines: list[str]
    settings: Settings

    def records(self, event=None):
        out = [json.loads(x) for x in self.lines]
        return [r for r in out if event is None or r["event"] == event]

    def fire(self, fp, status="firing"):
        r = self.client.post(URL, json=alert_body(fp, status=status), headers=HEADERS)
        return r.status_code, r.json()["results"][0]["outcome"]

    def settled(self):
        guard = self.app.state.guard

        def idle():
            with guard._lock:  # finish() empties the in-flight set and releases under this lock
                return not guard._inflight

        wait_until(idle)

    def handled(self):
        return json.loads(self.settings.state_file.read_text(encoding="utf-8"))


def wait_until(pred, timeout=10.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return
        time.sleep(0.01)
    raise AssertionError("condition not reached in time")


class OwnPrBranches(FakeBranchClient):
    """Any pull request number read back is a PR of the current run, in the configured repo."""

    ref = ""

    def get_pull_request(self, number):
        return {"head": {"ref": self.ref, "repo": {"full_name": "owner/repo"}}}


def real_rig(tmp_path: Path, behaviour=None, **over) -> Rig:
    settings = make_settings(tmp_path, mode="real", model=MODEL, repo="owner/repo",
                             anthropic_api_key="k", github_token="t", **over)
    backend = FakeBackend()
    backend.add_finding("42", ["failed"])
    api = ResponderApi(settings.api_url, settings.api_token, transport=httpx.MockTransport(backend.handler))
    script, lines = Script(behaviour), []
    script.branches = OwnPrBranches()
    app = create_app(settings, api=api, log=ActionLog(lines.append), make_session=script.make,
                     checkout_git=FakeCheckoutGit(), branches=script.branches)
    return Rig(app, TestClient(app), script, lines, settings)


# --- accepted straight away, run continues in the background -------------------

def test_the_response_arrives_while_the_run_is_still_in_flight(tmp_path):
    rig = real_rig(tmp_path, lambda s, fp: s.block(s, fp))
    code, outcome = rig.fire("fpA")
    assert (code, outcome) == (200, "accepted")
    assert rig.script.entered.wait(10)  # the agent is running now...
    assert rig.records("pull_request_opened") == []  # ...and has not finished
    rig.script.release.set()
    rig.settled()
    assert [r["outcome"] for r in rig.records("pull_request_opened")] == ["agent"]
    assert [r["event"] for r in rig.records() if r["event"] == "run_accepted"] == ["run_accepted"]


# --- the fingerprint stays claimed until the run ends -----------------------------

def test_a_repeat_firing_during_the_run_starts_no_second_run(tmp_path):
    rig = real_rig(tmp_path, lambda s, fp: s.block(s, fp))
    assert rig.fire("fpB") == (200, "accepted")
    assert rig.script.entered.wait(10)
    assert rig.fire("fpB") == (200, "repeat_ignored")  # the existing "already handled" answer
    rig.script.release.set()
    rig.settled()
    assert rig.script.started == ["fpB"]
    assert rig.fire("fpB") == (200, "repeat_ignored")  # still handled after a good run


def test_a_resolved_during_the_run_is_deferred_and_forgets_the_fingerprint_afterwards(tmp_path):
    rig = real_rig(tmp_path, lambda s, fp: s.block(s, fp))
    assert rig.fire("fpC") == (200, "accepted")
    assert rig.script.entered.wait(10)
    assert rig.fire("fpC", "resolved") == (200, "resolved_ignored")
    assert rig.app.state.guard._deferred == {"fpC"}  # deferred, not released mid-run
    assert "fpC" in rig.handled()
    rig.script.release.set()
    rig.settled()
    assert "fpC" not in rig.handled()  # forgotten once the run finished
    rig.script.behaviour = lambda s, fp: OK
    assert rig.fire("fpC") == (200, "accepted")  # a later firing runs again


# --- failures release the fingerprint and are logged -----------------------------

def _raise(s, fp):
    raise RuntimeError("sdk blew up")


def test_a_session_that_raises_releases_its_fingerprint_and_logs_the_failure(tmp_path):
    rig = real_rig(tmp_path, _raise)
    assert rig.fire("fpD") == (200, "accepted")
    rig.settled()
    assert "fpD" not in rig.handled()
    failed = rig.records("run_failed")
    assert failed and failed[0]["outcome"] == "error" and failed[0]["fingerprint"] == "fpD"


def test_a_session_that_ends_error_releases_its_fingerprint(tmp_path):
    rig = real_rig(tmp_path, lambda s, fp: AgentResult("error", MODEL))
    assert rig.fire("fpE") == (200, "accepted")
    rig.settled()
    assert "fpE" not in rig.handled()
    assert rig.records("run_failed")


def test_a_run_that_times_out_releases_its_fingerprint(tmp_path, monkeypatch):
    from vt_responder.real_runner import RealRunner

    original = RealRunner.__init__  # no extra grace period, so the 1 s limit is the whole wait
    monkeypatch.setattr(RealRunner, "__init__",
                        lambda self, *a, **k: original(self, *a, **{**k, "timeout_grace_seconds": 0.0}))

    def hang(s, fp):
        s.release.wait(10)
        return OK

    rig = real_rig(tmp_path, hang, run_timeout_seconds=1)
    assert rig.fire("fpF") == (200, "accepted")
    wait_until(lambda: rig.records("run_failed"), timeout=15)
    rig.script.release.set()
    rig.settled()
    assert [r["reason"] for r in rig.records("run_failed")] == ["agent_timeout"]
    assert "fpF" not in rig.handled()


def test_an_exception_out_of_the_runner_never_crashes_or_sticks(tmp_path, monkeypatch):
    from vt_responder.real_runner import RealRunner

    def boom(self, fp, fid):
        raise RuntimeError("runner crashed")

    monkeypatch.setattr(RealRunner, "run", boom)
    rig = real_rig(tmp_path)
    assert rig.fire("fpG") == (200, "accepted")
    rig.settled()
    assert "fpG" not in rig.handled()
    assert [r["reason"] for r in rig.records("run_failed")] == ["run_raised"]
    assert rig.app.state.guard.failed_runs("fpG") == 1
    assert rig.fire("fpH")[0] == 200  # the app still answers


def test_a_cancelled_session_never_crashes_or_sticks(tmp_path):
    def cancelled(s, fp):
        raise asyncio.CancelledError()

    rig = real_rig(tmp_path, cancelled)
    assert rig.fire("fpI") == (200, "accepted")
    rig.settled()
    assert "fpI" not in rig.handled()
    assert [r["reason"] for r in rig.records("run_failed")] == ["run_cancelled"]
    assert rig.app.state.guard.resolve("fpI") == "unknown"  # not left in flight
    assert rig.fire("fpI") == (200, "accepted")  # and a later firing is not a "repeat"


def test_a_queued_run_cancelled_at_shutdown_is_released_not_stuck(tmp_path):
    rig = real_rig(tmp_path, lambda s, fp: s.block(s, fp), max_concurrent_runs=1, max_queued_runs=2)
    with TestClient(rig.app) as client:  # the lifespan shuts the pool down on exit
        assert client.post(URL, json=alert_body("fpRun"), headers=HEADERS).json()["results"][0]["outcome"] == "accepted"
        assert rig.script.entered.wait(10)
        assert client.post(URL, json=alert_body("fpQ"), headers=HEADERS).json()["results"][0]["outcome"] == "accepted"
        assert "fpQ" in rig.handled()
    wait_until(lambda: "fpQ" not in rig.handled())  # the cancelled queued run was released
    assert rig.script.started == ["fpRun"]
    rig.script.release.set()
    rig.settled()


# --- retry cap ----------------------------------------------------------------------

def test_the_retry_cap_defaults_to_three_and_stops_the_fourth_run(tmp_path):
    assert make_settings(tmp_path).max_failed_runs == 3
    rig = real_rig(tmp_path, _raise)
    for n in (1, 2, 3):  # runs 1 to N start...
        assert rig.fire("fpJ") == (200, "accepted")
        rig.settled()
        assert len(rig.script.started) == n
    assert rig.fire("fpJ") == (200, "retry_cap_reached")  # ...run N+1 does not
    assert len(rig.script.started) == 3
    capped = rig.records("retry_cap_reached")
    assert len(capped) == 1 and capped[0]["fingerprint"] == "fpJ"
    assert "fpJ" not in rig.handled()  # not claimed either
    assert rig.fire("fpOther") == (200, "accepted")  # other fingerprints are unaffected


def test_a_resolved_lifts_the_retry_cap(tmp_path):
    rig = real_rig(tmp_path, _raise, max_failed_runs=1)
    assert rig.fire("fpK") == (200, "accepted")
    rig.settled()
    assert rig.fire("fpK") == (200, "retry_cap_reached")
    assert rig.fire("fpK", "resolved") == (200, "resolved_ignored")
    assert rig.fire("fpK") == (200, "accepted")


def test_a_good_run_resets_the_consecutive_failure_count(tmp_path):
    results = iter([AgentResult("error", MODEL), OK, AgentResult("error", MODEL), AgentResult("error", MODEL)])
    rig = real_rig(tmp_path, lambda s, fp: next(results), max_failed_runs=2)
    rig.fire("fpL")  # fail (1)
    rig.settled()
    rig.fire("fpL")  # success: count back to 0, fingerprint stays handled
    rig.settled()
    assert rig.app.state.guard.failed_runs("fpL") == 0
    rig.fire("fpL", "resolved")
    assert rig.fire("fpL") == (200, "accepted")  # fail (1)
    rig.settled()
    assert rig.fire("fpL") == (200, "accepted")  # fail (2)
    rig.settled()
    assert rig.fire("fpL") == (200, "retry_cap_reached")


# --- concurrency cap -------------------------------------------------------------------

def test_a_second_alert_is_queued_and_accepted_then_runs_after_the_first(tmp_path):
    rig = real_rig(tmp_path, lambda s, fp: s.block(s, fp), max_concurrent_runs=1, max_queued_runs=1)
    assert rig.fire("fp1") == (200, "accepted")
    assert rig.script.entered.wait(10)
    assert rig.fire("fp2") == (200, "accepted")  # queued behind fp1
    time.sleep(0.2)
    assert rig.script.started == ["fp1"]  # only one real run in flight
    assert {"fp1", "fp2"} <= set(rig.handled())  # both claimed
    rig.script.release.set()
    wait_until(lambda: rig.script.started == ["fp1", "fp2"])
    rig.settled()


def test_past_the_queue_limit_an_alert_is_refused_logged_and_released(tmp_path):
    rig = real_rig(tmp_path, lambda s, fp: s.block(s, fp), max_concurrent_runs=1, max_queued_runs=1)
    rig.fire("fp1")
    assert rig.script.entered.wait(10)
    rig.fire("fp2")
    assert rig.fire("fp3") == (503, "busy_refused")  # non-2xx: Grafana will re-send
    refused = rig.records("run_refused")
    assert len(refused) == 1 and refused[0]["fingerprint"] == "fp3" and refused[0]["reason"] == "queue_full"
    assert "fp3" not in rig.handled()  # released, so the re-send is not "already handled"
    rig.script.release.set()
    wait_until(lambda: rig.script.started == ["fp1", "fp2"])
    rig.settled()
    assert rig.fire("fp3") == (200, "accepted")  # the re-send runs
    rig.settled()


def test_two_runs_may_overlap_only_when_the_cap_is_raised(tmp_path):
    rig = real_rig(tmp_path, lambda s, fp: s.block(s, fp), max_concurrent_runs=2, max_queued_runs=0)
    rig.fire("fp1")
    rig.fire("fp2")
    wait_until(lambda: len(rig.script.started) == 2)
    assert rig.fire("fp3") == (503, "busy_refused")  # no queue
    rig.script.release.set()
    rig.settled()


# --- a run lost on restart is released, not stuck ----------------------------------------

def test_a_run_lost_on_restart_is_released_not_stuck(tmp_path):
    first = real_rig(tmp_path, lambda s, fp: s.block(s, fp))
    first.fire("fpLost")
    assert first.script.entered.wait(10)
    assert "fpLost" in first.handled()
    # "Restart" while the run is in flight: a new app and guard over the same record files.
    second = real_rig(tmp_path)
    assert [r["outcome"] for r in second.records("run_lost_on_restart")] == ["released"]
    assert second.records("run_lost_on_restart")[0]["fingerprint"] == "fpLost"
    assert second.fire("fpLost") == (200, "accepted")  # runs again; not "repeat_ignored" forever
    second.settled()
    assert second.script.started == ["fpLost"]
    first.script.release.set()
    first.settled()


def test_a_finished_run_is_still_handled_after_a_restart(tmp_path):
    first = real_rig(tmp_path)
    first.fire("fpDone")
    first.settled()
    second = real_rig(tmp_path)
    assert second.records("run_lost_on_restart") == []
    assert second.fire("fpDone") == (200, "repeat_ignored")


def test_guard_releases_only_in_flight_claims_on_restart(tmp_path):
    path = tmp_path / "g" / "handled.json"
    g = FingerprintGuard(path)
    assert g.claim("done") and g.claim("running")
    g.finish("done")
    g2 = FingerprintGuard(path)
    assert g2.lost_on_restart == ["running"]
    assert g2.claim("running") is True and g2.claim("done") is False
    assert FingerprintGuard(path).lost_on_restart == ["running"]  # g2's claim is itself in flight


def test_an_unreadable_in_flight_record_refuses_to_start(tmp_path):
    path = tmp_path / "handled.json"
    FingerprintGuard(path).claim("x")
    (tmp_path / "handled.json.inflight").write_text("not json", encoding="utf-8")
    with pytest.raises(RuntimeError):
        FingerprintGuard(path)


# --- guard additions -------------------------------------------------------------------------

def test_guard_counts_consecutive_failures_and_abandon_is_not_one(tmp_path):
    g = FingerprintGuard(tmp_path / "h.json")
    g.claim("a")
    g.finish("a", failed=True)
    g.finish("a", failed=True)  # a stray second finish is not a second failure
    assert g.failed_runs("a") == 1
    g.claim("a")
    g.abandon("a")
    assert g.failed_runs("a") == 1 and g.claim("a") is True
    g.finish("a")
    assert g.failed_runs("a") == 0
    g.claim("b")
    g.finish("b", failed=True)
    g.resolve("b")
    assert g.failed_runs("b") == 0


# --- configuration ------------------------------------------------------------------------------

REAL_ENV = {"RESPONDER_MODE": "real", "RESPONDER_WEBHOOK_SECRET": "s", "RESPONDER_API_TOKEN": "t",
            "RESPONDER_MODEL": MODEL, "ANTHROPIC_API_KEY": "k", "RESPONDER_GITHUB_TOKEN": "g",
            "RESPONDER_GITHUB_REPO": "owner/repo"}


def test_config_defaults_and_overrides():
    s = Settings.from_env(REAL_ENV)
    assert (s.max_failed_runs, s.max_concurrent_runs, s.max_queued_runs) == (3, 1, 10)
    s = Settings.from_env({**REAL_ENV, "RESPONDER_MAX_FAILED_RUNS": "5", "RESPONDER_MAX_CONCURRENT_RUNS": "2",
                           "RESPONDER_MAX_QUEUED_RUNS": "0"})
    assert (s.max_failed_runs, s.max_concurrent_runs, s.max_queued_runs) == (5, 2, 0)
    s = Settings.from_env({**REAL_ENV, "RESPONDER_MAX_FAILED_RUNS": ""})  # an empty .env entry means default
    assert s.max_failed_runs == 3


@pytest.mark.parametrize("name,value", [
    ("RESPONDER_MAX_FAILED_RUNS", "0"), ("RESPONDER_MAX_FAILED_RUNS", "x"),
    ("RESPONDER_MAX_CONCURRENT_RUNS", "0"), ("RESPONDER_MAX_QUEUED_RUNS", "-1"),
])
def test_config_refuses_bad_limits(name, value):
    with pytest.raises(ConfigError):
        Settings.from_env({**REAL_ENV, name: value})


def test_env_example_lists_the_new_names_with_no_value():
    text = (Path(__file__).resolve().parents[2] / ".env.example").read_text(encoding="utf-8")
    lines = text.splitlines()
    for name in ("RESPONDER_MAX_FAILED_RUNS", "RESPONDER_MAX_CONCURRENT_RUNS", "RESPONDER_MAX_QUEUED_RUNS"):
        assert f"{name}=" in lines
