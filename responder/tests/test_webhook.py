"""I-RESP-HOOK-* cases (task 28b, #219): the webhook receiver in stub mode."""

from __future__ import annotations

import threading

import httpx
import pytest
from fastapi.testclient import TestClient

from conftest import API_TOKEN, WEBHOOK_SECRET, FakeBackend, alert_body, make_rig, make_settings
from vt_responder.actlog import ActionLog
from vt_responder.api_client import ResponderApi
from vt_responder.app import create_app
from vt_responder.fakes import FakeGit, FakeGitHub

pytestmark = pytest.mark.unit

URL = "/webhook/grafana"


def post(rig, body, headers=None):
    return rig.client.post(URL, json=body, headers=rig.headers if headers is None else headers)


# --- I-RESP-HOOK-AUTH -------------------------------------------------------

@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": "Bearer wrong-token"},
    {"Authorization": f"Basic {WEBHOOK_SECRET}"},
    {"Authorization": "Bearer "},
    {"Authorization": WEBHOOK_SECRET},
])
def test_hook_auth_refuses_missing_or_wrong_token(rig, headers):
    rig.backend.add_finding("42", ["failed"])
    r = post(rig, alert_body(), headers=headers)
    assert r.status_code == 401
    assert rig.backend.requests == []  # no run started
    assert rig.git.calls == [] and rig.github.calls == []
    assert not rig.state_file.exists()  # fingerprint not claimed


def test_hook_auth_checks_token_before_reading_body(rig):
    # A bad token with an oversized/garbage body is still 401, not 413/400.
    r = rig.client.post(URL, content=b"x" * 10_000, headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_hook_auth_uses_constant_time_compare():
    import inspect
    from vt_responder import app
    assert "hmac.compare_digest" in inspect.getsource(app._token_ok)


def test_hook_auth_accepts_the_secret(rig):
    r = post(rig, alert_body(finding_id=None))
    assert r.status_code == 200


# --- I-RESP-HOOK-REPEAT -----------------------------------------------------

def test_hook_repeat_same_fingerprint_gives_one_run(rig):
    rig.backend.add_finding("42", ["failed"])
    first = post(rig, alert_body("fpA"))
    second = post(rig, alert_body("fpA"))
    assert first.json()["results"][0]["outcome"] == "pull_request_opened"
    assert second.json()["results"][0]["outcome"] == "repeat_ignored"
    assert len(rig.github.calls) == 1
    assert len([r for r in rig.records() if r["event"] == "run_started"]) == 1


def test_hook_repeat_record_survives_restart(tmp_path):
    first = make_rig(tmp_path)
    first.backend.add_finding("42", ["failed"])
    assert post(first, alert_body("fpR")).json()["results"][0]["outcome"] == "pull_request_opened"
    # "Restart": a brand-new app and guard over the same state file.
    second = make_rig(tmp_path)
    second.backend.add_finding("42", ["failed"])
    r = post(second, alert_body("fpR"))
    assert r.json()["results"][0]["outcome"] == "repeat_ignored"
    assert second.backend.requests == [] and second.github.calls == []


def test_hook_repeat_different_fingerprints_each_run(rig):
    rig.backend.add_finding("42", ["failed"])
    post(rig, alert_body("fp1"))
    post(rig, alert_body("fp2"))
    assert [c[1]["branch"] for c in rig.github.calls] == ["responder/fp1", "responder/fp2"]


def test_hook_repeat_failed_run_is_released_so_a_resend_retries(rig):
    rig.backend.add_finding("42", ["failed"])
    rig.backend.fail_status = 500
    assert post(rig, alert_body("fpE")).json()["results"][0]["outcome"] == "error"
    rig.backend.fail_status = None
    assert post(rig, alert_body("fpE")).json()["results"][0]["outcome"] == "pull_request_opened"


# --- I-RESP-HOOK-RESOLVED / -MALFORMED / -SIZE ------------------------------

def test_hook_resolved_starts_no_run(rig):
    rig.backend.add_finding("42", ["failed"])
    r = post(rig, alert_body(status="resolved"))
    assert r.status_code == 200
    assert r.json()["results"][0]["outcome"] == "resolved_ignored"
    assert rig.backend.requests == [] and rig.git.calls == [] and rig.github.calls == []
    assert not rig.state_file.exists()
    assert [x["event"] for x in rig.records()] == ["alert_ignored"]


def test_hook_resolved_does_not_burn_the_fingerprint(rig):
    rig.backend.add_finding("42", ["failed"])
    post(rig, alert_body("fpX", status="resolved"))
    assert post(rig, alert_body("fpX")).json()["results"][0]["outcome"] == "pull_request_opened"


def outcome(rig, body):
    return post(rig, body).json()["results"][0]["outcome"]


def test_hook_resolved_forgets_the_fingerprint_so_a_refiring_runs_again(rig):
    rig.backend.add_finding("42", ["failed"])
    assert outcome(rig, alert_body("fpF")) == "pull_request_opened"
    assert outcome(rig, alert_body("fpF")) == "repeat_ignored"  # firing, firing: one run
    requests_before = len(rig.backend.requests)
    assert outcome(rig, alert_body("fpF", status="resolved")) == "resolved_ignored"
    assert len(rig.backend.requests) == requests_before  # resolved reads no API
    assert len(rig.github.calls) == 1  # and starts no run
    assert outcome(rig, alert_body("fpF")) == "pull_request_opened"  # firing, resolved, firing: two runs
    assert len(rig.github.calls) == 2
    ignored = [r for r in rig.records() if r["event"] == "alert_ignored" and r["outcome"] == "resolved"]
    assert len(ignored) == 1


def test_hook_resolved_for_unknown_fingerprint_is_harmless(rig):
    rig.backend.add_finding("42", ["failed"])
    assert outcome(rig, alert_body("fpK")) == "pull_request_opened"
    before = rig.state_file.read_text()
    assert outcome(rig, alert_body("fpUnknown", status="resolved")) == "resolved_ignored"
    assert rig.state_file.read_text() == before  # no record change
    assert outcome(rig, alert_body("fpK")) == "repeat_ignored"


def test_hook_resolved_release_survives_restart(tmp_path):
    first = make_rig(tmp_path)
    first.backend.add_finding("42", ["failed"])
    assert outcome(first, alert_body("fpGone")) == "pull_request_opened"
    assert outcome(first, alert_body("fpKept")) == "pull_request_opened"
    post(first, alert_body("fpGone", status="resolved"))
    second = make_rig(tmp_path)  # a new app and guard over the same record file
    second.backend.add_finding("42", ["failed"])
    assert outcome(second, alert_body("fpKept")) == "repeat_ignored"
    assert outcome(second, alert_body("fpGone")) == "pull_request_opened"


def test_hook_resolved_and_firing_in_one_body_are_handled_each(rig):
    rig.backend.add_finding("42", ["failed"])
    assert outcome(rig, alert_body("fpOld")) == "pull_request_opened"
    body = alert_body("fpNew")
    body["alerts"].append(alert_body("fpOld", status="resolved")["alerts"][0])
    r = post(rig, body)
    assert [x["outcome"] for x in r.json()["results"]] == ["pull_request_opened", "resolved_ignored"]
    assert outcome(rig, alert_body("fpOld")) == "pull_request_opened"  # fpOld was released
    assert outcome(rig, alert_body("fpNew")) == "repeat_ignored"  # fpNew is still guarded


# --- resolved while a run is in flight (deferred release) --------------------

class _BlockingGitHub(FakeGitHub):
    """Holds the first run inside ``open_pull_request`` until the test lets it go."""

    def __init__(self) -> None:
        super().__init__()
        self.entered = threading.Event()
        self.release_run = threading.Event()
        self.block = True

    def open_pull_request(self, branch, title, body):
        if self.block:
            self.block = False  # only the first run blocks
            self.entered.set()
            assert self.release_run.wait(10), "test never released the run"
        return super().open_pull_request(branch, title, body)


def _inflight_rig(tmp_path, fail_after_release=False):
    settings = make_settings(tmp_path)
    backend = FakeBackend()
    api = ResponderApi(settings.api_url, settings.api_token, transport=httpx.MockTransport(backend.handler))
    github, lines = _BlockingGitHub(), []
    app = create_app(settings, api=api, git=FakeGit(), github=github, log=ActionLog(lines.append))
    backend.add_finding("42", ["failed"])
    return TestClient(app), backend, github, settings


def _start_blocked_run(client, github, fp):
    box = {}
    t = threading.Thread(target=lambda: box.update(r=client.post(URL, json=alert_body(fp), headers=HEADERS)))
    t.start()
    assert github.entered.wait(10), "the run never started"
    return t, box


HEADERS = {"Authorization": f"Bearer {WEBHOOK_SECRET}"}


def _out(client, fp, status="firing"):
    return client.post(URL, json=alert_body(fp, status=status), headers=HEADERS).json()["results"][0]["outcome"]


def test_hook_resolved_in_flight_defers_the_release_until_the_run_ends(tmp_path):
    client, _backend, github, _s = _inflight_rig(tmp_path)
    t, box = _start_blocked_run(client, github, "fpI")
    assert _out(client, "fpI", "resolved") == "resolved_ignored"  # arrives mid-run
    assert _out(client, "fpI") == "repeat_ignored"  # no second concurrent run...
    github.release_run.set()
    t.join(10)
    assert box["r"].json()["results"][0]["outcome"] == "pull_request_opened"
    # ...but that firing came after the resolved, so it cancelled the deferred release.
    assert _out(client, "fpI") == "repeat_ignored"
    assert len(github.calls) == 1


def test_hook_resolved_in_flight_releases_when_the_run_ends(tmp_path):
    client, _backend, github, _s = _inflight_rig(tmp_path)
    t, box = _start_blocked_run(client, github, "fpJ")
    assert _out(client, "fpJ", "resolved") == "resolved_ignored"
    github.release_run.set()
    t.join(10)
    assert box["r"].json()["results"][0]["outcome"] == "pull_request_opened"
    assert _out(client, "fpJ") == "pull_request_opened"  # released after the run: a new run
    assert len(github.calls) == 2


def test_hook_resolved_in_flight_second_firing_ignored_then_third_runs(tmp_path):
    client, _backend, github, _s = _inflight_rig(tmp_path)
    t, _box = _start_blocked_run(client, github, "fpH")
    assert _out(client, "fpH") == "repeat_ignored"  # second firing, run still in flight
    assert _out(client, "fpH", "resolved") == "resolved_ignored"
    github.release_run.set()
    t.join(10)
    assert _out(client, "fpH") == "pull_request_opened"  # third firing starts a new run


def test_hook_resolved_in_flight_with_an_error_releases_once(tmp_path):
    client, backend, github, settings = _inflight_rig(tmp_path)
    backend.fail_status = 500
    # The error path never reaches the (blocking) GitHub call, so drive the guard directly
    # to hold the run open: claim, resolve (deferred), then finish as failed.
    guard = client.app.state.guard
    assert guard.claim("fpD") is True
    assert guard.resolve("fpD") == "deferred"
    guard.finish("fpD", failed=True)  # error plus deferred release: one release, no error
    guard.finish("fpD", failed=True)  # a stray second finish is harmless
    backend.fail_status = None
    github.block = False
    assert _out(client, "fpD") == "pull_request_opened"
    assert settings.state_file.exists()


class _RaisingOnceGitHub(FakeGitHub):
    """Makes the first run raise out of ``runner.run`` (not return ``"error"``)."""

    def __init__(self) -> None:
        super().__init__()
        self.raise_next = True

    def open_pull_request(self, branch, title, body):
        if self.raise_next:
            self.raise_next = False
            raise RuntimeError("boom: the run crashed")
        return super().open_pull_request(branch, title, body)


def test_hook_run_that_raises_releases_the_fingerprint_and_clears_in_flight(tmp_path):
    # #234 raise path: an exception out of runner.run (not an "error" outcome) must not
    # leave the fingerprint claimed or the run marked in flight. The webhook answers 500
    # (the exception propagates out of the handler; the client is told to retry).
    settings = make_settings(tmp_path)
    backend = FakeBackend()
    backend.add_finding("42", ["failed"])
    api = ResponderApi(settings.api_url, settings.api_token, transport=httpx.MockTransport(backend.handler))
    github = _RaisingOnceGitHub()
    app = create_app(settings, api=api, git=FakeGit(), github=github, log=ActionLog(lambda s: None))
    client = TestClient(app, raise_server_exceptions=False)  # see the real 500, not a re-raise

    r = client.post(URL, json=alert_body("fpX1"), headers=HEADERS)
    assert r.status_code == 500
    assert github.raise_next is False  # the raising path really ran

    # Fingerprint released from the persisted record, so a restart would not see it either.
    assert "fpX1" not in settings.state_file.read_text(encoding="utf-8")
    # In-flight state cleared: a resolved now is "unknown" (nothing recorded), not "deferred"
    # (which it would be if the run were still marked in flight, and would then hang forever).
    assert app.state.guard.resolve("fpX1") == "unknown"
    # A later firing is not a repeat: it starts a new run, which completes.
    r2 = client.post(URL, json=alert_body("fpX1"), headers=HEADERS)
    assert r2.status_code == 200
    assert r2.json()["results"][0]["outcome"] == "pull_request_opened"
    assert len(github.calls) == 1


@pytest.mark.parametrize("raw", [
    b"not json",
    b"[]",
    b"{}",
    b'{"status":"firing","alerts":[]}',
    b'{"status":"weird","alerts":[{"fingerprint":"a"}]}',
    b'{"status":"firing","alerts":["x"]}',
    # US-15 change (#219): an alert with no fingerprint AND no finding_id used to be 400 here
    # (b'{"labels":{}}'); it is now a 200 "no change" (see the NOCHANGE cases). A finding_id
    # without a fingerprint stays 400 because the run cannot be guarded against repeats.
    b'{"status":"firing","alerts":[{"labels":{"finding_id":"42"}}]}',
    b'{"status":"firing","alerts":[{"fingerprint":"../etc/passwd"}]}',
    b'{"status":"firing","alerts":[{"fingerprint":"../etc/passwd","labels":{}}]}',
    b'{"status":"firing","alerts":[{"fingerprint":"","labels":{}}]}',
    b'{"status":"firing","alerts":[{"fingerprint":7,"labels":{}}]}',
    b'{"status":"firing","alerts":[{"labels":{"finding_id":"1/../2"}}]}',
    b'{"status":"firing","alerts":[{"fingerprint":"ok","labels":{"finding_id":"1/../2"}}]}',
    b'{"status":"firing","alerts":[{"fingerprint":"ok","labels":"x"}]}',
])
def test_hook_malformed_payload_gets_400_and_no_run(rig, raw):
    r = rig.client.post(URL, content=raw, headers=rig.headers)
    assert r.status_code == 400
    assert rig.backend.requests == [] and rig.github.calls == []
    assert not rig.state_file.exists()


@pytest.mark.parametrize("fingerprint", ["ok\n", "ok\r\n", "\n"])
def test_hook_malformed_fingerprint_with_newline_gets_400_and_no_run(rig, fingerprint):
    # `$` matches before a trailing newline; the fingerprint becomes a branch name (#221).
    rig.backend.add_finding("42", ["failed"])
    r = post(rig, alert_body(fingerprint))
    assert r.status_code == 400
    assert rig.backend.requests == [] and rig.git.calls == [] and rig.github.calls == []
    assert not rig.state_file.exists()  # no guard record


def test_hook_malformed_finding_id_with_newline_gets_400_and_no_run(rig):
    rig.backend.add_finding("1", ["failed"])
    r = post(rig, alert_body("fpN", finding_id="1\n"))
    assert r.status_code == 400
    assert rig.backend.requests == [] and rig.git.calls == [] and rig.github.calls == []
    assert not rig.state_file.exists()


def test_hook_valid_ids_are_still_accepted(rig):
    rig.backend.add_finding("42", ["failed"])
    r = post(rig, alert_body("ok_-9"))
    assert r.status_code == 200
    assert r.json()["results"][0]["outcome"] == "pull_request_opened"


def test_hook_malformed_alert_blocks_the_whole_payload(rig):
    rig.backend.add_finding("42", ["failed"])
    body = alert_body("good")
    body["alerts"].append({"status": "firing", "fingerprint": "bad/one", "labels": {}})
    assert post(rig, body).status_code == 400
    assert rig.github.calls == []


def test_hook_oversized_body_gets_413(rig):
    body = alert_body()
    body["pad"] = "x" * 10_000  # settings cap is 4096 in the rig
    r = post(rig, body)
    assert r.status_code == 413
    assert rig.backend.requests == [] and rig.github.calls == []


def test_hook_oversized_body_without_content_length_gets_413(rig):
    def chunks():
        yield b'{"status":"firing","alerts":['
        for _ in range(10):
            yield b" " * 1000
    r = rig.client.post(URL, content=chunks(), headers=rig.headers)  # chunked, no Content-Length
    assert r.status_code == 413


# --- I-RESP-HOOK-STUBREAD ---------------------------------------------------

def test_hook_stub_reads_only_the_two_allowed_operations_with_the_token(rig):
    rig.backend.add_finding("42", ["failed", "sent"])
    post(rig, alert_body())
    reqs = rig.backend.requests
    assert [(r.method, r.url.path) for r in reqs] == [
        ("GET", "/responder/findings/42"),
        ("GET", "/responder/notification-jobs"),
    ]
    assert reqs[1].url.params["findingId"] == "42"
    assert all(r.headers["authorization"] == f"Bearer {API_TOKEN}" for r in reqs)


# --- I-RESP-HOOK-NOCHANGE ---------------------------------------------------

def _assert_no_change(rig, expect_api_calls):
    results = rig.records()
    no_change = [r for r in results if r["event"] == "no_change"]
    assert len(no_change) == 1
    assert no_change[0]["outcome"] == "no_change"
    assert len(no_change[0]["explanation"]) > 40  # says what was checked and why no defect
    assert rig.git.calls == [] and rig.github.calls == []  # no branch, commit, PR or push
    assert len(rig.backend.requests) == expect_api_calls
    assert not any(r["event"] in ("branch_recorded", "pull_request_opened") for r in results)


def test_hook_nochange_alert_without_finding_id(rig):
    r = post(rig, alert_body("fpT", finding_id=None))
    assert r.json()["results"][0]["outcome"] == "no_change"
    _assert_no_change(rig, expect_api_calls=0)
    assert "finding_id" in [x for x in rig.records() if x["event"] == "no_change"][0]["explanation"]


@pytest.mark.parametrize("alert", [
    {"status": "firing", "labels": {"alertname": "TestAlert"}},
    {"status": "firing", "labels": {}},
    {"status": "firing"},
    {"status": "firing", "fingerprint": None, "labels": {"finding_id": None}},
])
def test_hook_nochange_alert_without_fingerprint_or_finding_id(rig, alert):
    # US-15: a test alert may carry no fingerprint; explain and change nothing, not 400.
    rig.backend.add_finding("42", ["failed"])
    r = rig.client.post(URL, json={"status": "firing", "alerts": [alert]}, headers=rig.headers)
    assert r.status_code == 200
    assert r.json()["results"] == [{"fingerprint": None, "outcome": "no_change"}]
    _assert_no_change(rig, expect_api_calls=0)
    assert not rig.state_file.exists()  # the repeat guard record is untouched
    rec = [x for x in rig.records() if x["event"] == "no_change"][0]
    assert rec["fingerprint"] is None and rec["finding_id"] is None
    assert "neither a fingerprint nor a finding_id" in rec["explanation"]
    assert "run_started" not in [x["event"] for x in rig.records()]


def test_hook_nochange_without_ids_leaves_existing_guard_record_unchanged(rig):
    rig.backend.add_finding("42", ["failed"])
    post(rig, alert_body("fpK"))  # a real run claims fpK
    before = rig.state_file.read_text(encoding="utf-8")
    calls = (len(rig.git.calls), len(rig.github.calls), len(rig.backend.requests))
    body = {"status": "firing", "alerts": [{"status": "firing", "labels": {}}]}
    assert post(rig, body).json()["results"][0]["outcome"] == "no_change"
    assert post(rig, body).json()["results"][0]["outcome"] == "no_change"  # not a "repeat": nothing is guarded
    assert rig.state_file.read_text(encoding="utf-8") == before
    assert (len(rig.git.calls), len(rig.github.calls), len(rig.backend.requests)) == calls


def test_hook_nochange_resolved_without_ids_is_ignored(rig):
    body = {"status": "resolved", "alerts": [{"status": "resolved", "labels": {}}]}
    r = post(rig, body)
    assert r.status_code == 200
    assert r.json()["results"] == [{"fingerprint": None, "outcome": "resolved_ignored"}]
    assert rig.backend.requests == [] and rig.git.calls == [] and rig.github.calls == []
    assert not rig.state_file.exists()
    assert [x["event"] for x in rig.records()] == ["alert_ignored"]


def test_hook_nochange_without_ids_mixed_with_a_real_alert(rig):
    rig.backend.add_finding("42", ["failed"])
    body = alert_body("fpM2")
    body["alerts"].append({"status": "firing", "labels": {}})
    outcomes = [x["outcome"] for x in post(rig, body).json()["results"]]
    assert outcomes == ["pull_request_opened", "no_change"]
    assert rig.state_file.read_text(encoding="utf-8") == '["fpM2"]'


def test_hook_nochange_finding_id_without_fingerprint_is_400(rig):
    rig.backend.add_finding("42", ["failed"])
    body = {"status": "firing", "alerts": [{"status": "firing", "labels": {"finding_id": "42"}}]}
    assert post(rig, body).status_code == 400
    assert rig.backend.requests == [] and rig.git.calls == [] and rig.github.calls == []
    assert not rig.state_file.exists()


def test_hook_nochange_finding_without_failed_job(rig):
    rig.backend.add_finding("42", ["sent", "pending"])
    r = post(rig, alert_body())
    assert r.json()["results"][0]["outcome"] == "no_change"
    _assert_no_change(rig, expect_api_calls=2)
    assert "none is in state failed" in [x for x in rig.records() if x["event"] == "no_change"][0]["explanation"]


def test_hook_nochange_finding_with_no_jobs(rig):
    rig.backend.add_finding("42", [])
    assert post(rig, alert_body()).json()["results"][0]["outcome"] == "no_change"
    _assert_no_change(rig, expect_api_calls=2)


def test_hook_nochange_unknown_finding(rig):
    assert post(rig, alert_body(finding_id="999")).json()["results"][0]["outcome"] == "no_change"
    _assert_no_change(rig, expect_api_calls=1)


# --- I-RESP-HOOK-DEFECT -----------------------------------------------------

def test_hook_defect_path_records_branch_files_and_fake_pull_request(rig):
    rig.backend.add_finding("42", ["failed"])
    r = post(rig, alert_body("fpD"))
    assert r.json()["results"][0]["outcome"] == "pull_request_opened"
    assert [c[0] for c in rig.git.calls] == ["create_branch", "commit"]  # never push
    assert rig.git.calls[0][1] == {"name": "responder/fpD"}
    commit = rig.git.calls[1][1]
    assert commit["branch"] == "responder/fpD"
    assert len(commit["files"]) == 2 and any("test" in f for f in commit["files"])
    assert [c[0] for c in rig.github.calls] == ["open_pull_request"]
    assert rig.github.calls[0][1]["branch"] == "responder/fpD"
    events = {x["event"]: x for x in rig.records()}
    assert events["branch_recorded"]["branch"] == "responder/fpD"
    assert events["branch_recorded"]["test_file"] and events["branch_recorded"]["fix_file"]
    assert events["pull_request_opened"]["outcome"] == "stub"


# --- I-RESP-HOOK-LOG --------------------------------------------------------

def test_hook_log_one_json_line_per_action_with_no_secret_or_advisory_text(rig):
    rig.backend.add_finding("42", ["failed"])
    post(rig, alert_body("fpL"))  # defect path
    post(rig, alert_body("fpL"))  # repeat
    post(rig, alert_body("fpM", status="resolved"))
    post(rig, alert_body("fpN", finding_id=None))  # no change
    post(rig, alert_body("fpO"), headers={"Authorization": "Bearer WRONG-TOKEN-zz9"})  # 401
    post(rig, {"status": "firing", "alerts": []})  # 400
    blob = "\n".join(rig.log_lines)
    for planted in (WEBHOOK_SECRET, API_TOKEN, "WRONG-TOKEN-zz9", "ADVISORY-TEXT-MARKER", "rm -rf"):
        assert planted not in blob
    records = rig.records()  # every line parses as JSON
    assert records
    for rec in records:
        assert {"ts", "event", "fingerprint", "finding_id", "outcome"} <= rec.keys()
    assert "Authorization" not in blob and "Bearer" not in blob
    events = [r["event"] for r in records]
    for expected in ("run_started", "api_read", "branch_recorded", "pull_request_opened", "alert_ignored",
                     "no_change", "webhook_rejected"):
        assert expected in events


def test_hook_log_api_error_logs_no_response_body(rig):
    rig.backend.add_finding("42", ["failed"])
    rig.backend.fail_status = 500  # body is the advisory marker text
    post(rig, alert_body("fpZ"))
    blob = "\n".join(rig.log_lines)
    assert "ADVISORY-TEXT-MARKER" not in blob
    assert [r for r in rig.records() if r["event"] == "run_failed"][0]["outcome"] == "error"


def test_hook_log_refuses_unknown_fields():
    from vt_responder.actlog import ActionLog
    with pytest.raises(ValueError):
        ActionLog(lambda s: None).emit("x", outcome="ok", token="secret")
