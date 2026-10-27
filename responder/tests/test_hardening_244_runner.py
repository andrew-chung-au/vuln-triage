"""#244 S2, S3, S6: install before the session, stop the agent first, spend cap, redaction.

Everything here is a fake or a real throwaway process; no SDK, no key, no network.
What these tests cannot prove (no live SDK): that the marker reaches the real CLI and
its children and that killing them ends a live session. That stays a drill check.
"""

from __future__ import annotations

import base64
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest

from vt_responder.actlog import ActionLog
from vt_responder.api_client import ResponderApi
from vt_responder.config import DEFAULT_MAX_BUDGET_USD, ConfigError, Settings
from vt_responder.envscrub import minimal_env, redact
from vt_responder.fakes import FakeBranchClient
from vt_responder.installer import InstallError, SubprocessInstaller
from vt_responder.policy import ToolPolicy
from vt_responder.procs import MARKER_VAR, kill_marked_processes
from vt_responder.real_runner import AgentResult, RealRunner
from vt_responder.sdk_session import build_options

from conftest import FakeBackend
from test_real_runner_isolation import BRANCH, MODEL, FakeCheckoutGit, Session, events
from test_sdk_session import KEY, TOKEN, FakeSdk, make_ctx

pytestmark = pytest.mark.unit

PACKAGE_ROOT = str(Path(__file__).resolve().parents[1])


def make_runner(behaviour, *, order=None, git=None, branches=None, installer=None, kill=None, timeout=5,
                secrets=(), lines=None):
    backend = FakeBackend()
    backend.add_finding("42", ["failed"])
    api = ResponderApi("http://backend.test", "tok", transport=httpx.MockTransport(backend.handler))
    lines = [] if lines is None else lines
    contexts = []

    def make(model, ctx):
        contexts.append(ctx)
        return Session(behaviour)

    kwargs = {}
    if kill is not None:
        kwargs["kill_agent"] = kill
    runner = RealRunner(api, ActionLog(lines.append), MODEL, make, git=git or FakeCheckoutGit(),
                        branches=branches if branches is not None else FakeBranchClient(),
                        timeout_seconds=timeout, timeout_grace_seconds=0.0, installer=installer,
                        secrets=secrets, **kwargs)
    return runner, lines, contexts


# -- S2: clone -> install -> session -------------------------------------------

class RecordingGit(FakeCheckoutGit):
    def __init__(self, order):
        super().__init__()
        self.order = order

    def clone(self, dest):
        self.order.append("clone")
        super().clone(dest)


class FakeInstaller:
    def __init__(self, order, fail=False):
        self.order, self.fail, self.seen = order, fail, []

    def install(self, checkout, *, timeout):
        self.order.append("install")
        self.seen.append((checkout, checkout.exists(), timeout))
        if self.fail:
            raise InstallError("install failed")


def test_s2_the_runner_installs_between_the_clone_and_the_session():
    order = []
    installer = FakeInstaller(order)

    def behaviour(s):
        order.append("session")
        return AgentResult("no_change", MODEL, explanation="x")

    runner, lines, ctxs = make_runner(behaviour, git=RecordingGit(order), installer=installer)
    assert runner.run("fp1", "42") == "no_change"
    assert order == ["clone", "install", "session"]
    assert installer.seen[0][1] is True  # it installed into the live checkout
    assert ctxs[0].timeout_seconds <= 5  # the install's time came out of the run's limit


def test_s2_a_failed_install_is_an_error_with_no_session_and_no_branch():
    order = []
    branches = FakeBranchClient()
    runner, lines, ctxs = make_runner(lambda s: order.append("session"), git=RecordingGit(order),
                                      installer=FakeInstaller(order, fail=True), branches=branches)
    assert runner.run("fp1", "42") == "error"
    assert order == ["clone", "install"]  # the agent never started
    assert ctxs == [] and branches.branches == {} and branches.deleted == []
    assert [e["reason"] for e in events(lines) if e["event"] == "run_failed"] == ["install_failed"]


def test_s2_the_install_environment_holds_no_secret(monkeypatch):
    for name in ("ANTHROPIC_API_KEY", "GH_TOKEN", "RESPONDER_GITHUB_TOKEN", "RESPONDER_API_TOKEN",
                 "GIT_CONFIG_VALUE_0", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.setenv(name, "PLANTED-" + name)
    code = ("import os, sys; "
            "bad = [k for k in os.environ if k in ('ANTHROPIC_API_KEY','GH_TOKEN','RESPONDER_GITHUB_TOKEN',"
            "'RESPONDER_API_TOKEN','GIT_CONFIG_VALUE_0','AWS_SECRET_ACCESS_KEY')]; "
            "sys.exit(1 if bad else 0)")
    SubprocessInstaller([sys.executable, "-c", code]).install(Path.cwd(), timeout=20)  # raises if one leaked
    assert "ANTHROPIC_API_KEY" not in minimal_env(os.environ)


def test_s2_a_failing_or_overlong_install_raises_without_output():
    with pytest.raises(InstallError, match="install failed"):
        SubprocessInstaller([sys.executable, "-c", "print('SECRET-OUTPUT'); raise SystemExit(3)"]).install(
            Path.cwd(), timeout=20)
    started = time.monotonic()
    with pytest.raises(InstallError, match="timed out"):
        SubprocessInstaller([sys.executable, "-c", "import time; time.sleep(60)"]).install(Path.cwd(), timeout=0.3)
    assert time.monotonic() - started < 10
    with pytest.raises(InstallError, match="could not start"):
        SubprocessInstaller(["/nonexistent/binary"]).install(Path.cwd(), timeout=5)


@pytest.mark.parametrize("cmd", ["make install", "make backend-install", "uv sync", "uv run pytest", "npm ci",
                                 "npm install", "pytest", "pytest responder/tests", "python3 -m pytest"])
def test_s2_the_agent_is_still_denied_installs_and_pytest(tmp_path, cmd):
    (tmp_path / "backend").mkdir()
    assert not ToolPolicy(tmp_path, "fp1").check("Bash", {"command": cmd}).allowed


# -- S3: kill first, then the checkout, then the branch -------------------------

def test_s3_the_agent_is_killed_before_the_checkout_goes_and_the_branch_is_deleted():
    order = []
    release = threading.Event()
    branches = FakeBranchClient()
    git = FakeCheckoutGit()
    snapshot = {}

    def kill(marker):
        # At kill time the checkout must still exist and the branch must not be deleted yet.
        snapshot["checkout_exists"] = git.dests[0].exists()
        snapshot["deleted_so_far"] = list(branches.deleted)
        order.append("kill")
        release.set()  # a killed agent stops; before this it ignored cancellation

    class Delete(FakeBranchClient):
        def delete_branch_if_exists(self, branch):
            order.append("delete_branch")
            return super().delete_branch_if_exists(branch)

    branches = Delete()

    def ignores_cancellation(s):
        branches.push(BRANCH)
        while not release.wait(0.05):  # stands in for an agent that keeps going after the timeout
            pass
        order.append("agent_stopped")
        return AgentResult("pull_request_opened", MODEL, pull_request="https://pr/1")

    runner, lines, _ = make_runner(ignores_cancellation, git=git, branches=branches, kill=kill, timeout=0.2)
    try:
        assert runner.run("fp1", "42") == "error"
    finally:
        release.set()
    assert snapshot == {"checkout_exists": True, "deleted_so_far": []}
    assert order.index("kill") < order.index("delete_branch")
    assert not git.dests[0].exists()
    assert branches.deleted == [BRANCH]
    assert [e["reason"] for e in events(lines) if e["event"] == "run_failed"] == ["agent_timeout"]


def test_s3_the_agent_is_stopped_after_a_normal_finish_too():
    killed = []
    runner, lines, ctxs = make_runner(lambda s: AgentResult("no_change", MODEL, explanation="x"),
                                      kill=killed.append)
    runner.run("fp1", "42")
    assert killed == [ctxs[0].run_marker] and ctxs[0].run_marker


def test_s3_a_failing_kill_is_logged_and_does_not_stop_the_cleanup():
    def kill(marker):
        raise OSError("no /proc")

    branches = FakeBranchClient()

    def behaviour(s):
        branches.push(BRANCH)
        raise RuntimeError("boom")

    runner, lines, _ = make_runner(behaviour, kill=kill, branches=branches)
    assert runner.run("fp1", "42") == "error"
    assert branches.deleted == [BRANCH]
    assert any(e["event"] == "agent_kill_failed" for e in events(lines))


def test_s3_marked_processes_are_killed_and_others_are_not():
    marker = "test-marker-" + os.urandom(6).hex()
    sleeper = [sys.executable, "-c", "import time; time.sleep(60)"]
    marked = subprocess.Popen(sleeper, env={**os.environ, MARKER_VAR: marker})
    other = subprocess.Popen(sleeper, env={**os.environ, MARKER_VAR: marker + "-other"})
    plain = subprocess.Popen(sleeper)
    try:
        assert kill_marked_processes(marker) == 1
        assert marked.wait(timeout=10) == -9
        assert other.poll() is None and plain.poll() is None
        assert kill_marked_processes("") == 0
    finally:
        for p in (marked, other, plain):
            p.kill()
            p.wait()


def test_s3_the_run_marker_reaches_the_agent_environment(tmp_path):
    ctx = make_ctx(tmp_path, run_marker="abc123")
    env = build_options(FakeSdk([]), model=MODEL, system_prompt="s", ctx=ctx, api_key=KEY,
                        github_token=TOKEN).kwargs["env"]
    assert env[MARKER_VAR] == "abc123"


def test_s3_the_spend_cap_is_passed_to_the_sdk(tmp_path):
    ctx = make_ctx(tmp_path, max_budget_usd=1.25)
    kwargs = build_options(FakeSdk([]), model=MODEL, system_prompt="s", ctx=ctx, api_key=KEY,
                           github_token=TOKEN).kwargs
    assert kwargs["max_budget_usd"] == 1.25


def test_s3_the_real_sdk_options_accept_the_spend_cap(tmp_path):
    sdk = pytest.importorskip("claude_agent_sdk")  # catches a misspelt option name
    ctx = make_ctx(tmp_path, max_budget_usd=2.5)
    opts = build_options(sdk, model=MODEL, system_prompt="s", ctx=ctx, api_key=KEY, github_token=TOKEN)
    assert opts.max_budget_usd == 2.5


def test_s3_the_runner_hands_the_configured_cap_to_the_session():
    seen = []
    runner, lines, ctxs = make_runner(lambda s: AgentResult("no_change", MODEL, explanation="x"))
    runner._budget = 0.75
    runner.run("fp1", "42")
    assert ctxs[0].max_budget_usd == 0.75
    runner2, _, ctxs2 = make_runner(lambda s: AgentResult("no_change", MODEL, explanation="x"))
    runner2.run("fp1", "42")
    assert ctxs2[0].max_budget_usd == DEFAULT_MAX_BUDGET_USD


REAL_ENV = {"RESPONDER_MODE": "real", "RESPONDER_WEBHOOK_SECRET": "w", "RESPONDER_API_TOKEN": "t",
            "RESPONDER_MODEL": MODEL, "ANTHROPIC_API_KEY": "k", "RESPONDER_GITHUB_TOKEN": "g",
            "RESPONDER_GITHUB_REPO": "o/r"}


def test_s3_the_budget_setting_has_a_default_and_rejects_bad_values():
    assert Settings.from_env(REAL_ENV).max_budget_usd == DEFAULT_MAX_BUDGET_USD
    assert Settings.from_env({**REAL_ENV, "RESPONDER_MAX_BUDGET_USD": ""}).max_budget_usd == DEFAULT_MAX_BUDGET_USD
    assert Settings.from_env({**REAL_ENV, "RESPONDER_MAX_BUDGET_USD": "0.5"}).max_budget_usd == 0.5
    for bad in ("0", "-1", "x", "nan", "inf"):
        with pytest.raises(ConfigError):
            Settings.from_env({**REAL_ENV, "RESPONDER_MAX_BUDGET_USD": bad})


def test_s3_an_abandoned_worker_does_not_keep_the_interpreter_alive():
    code = (
        "import threading, httpx\n"
        "from vt_responder.actlog import ActionLog\n"
        "from vt_responder.api_client import ResponderApi\n"
        "from vt_responder.real_runner import RealRunner\n"
        "from conftest import FakeBackend\n"
        "from test_real_runner_isolation import FakeCheckoutGit\n"
        "b = FakeBackend(); b.add_finding('42', ['failed'])\n"
        "api = ResponderApi('http://backend.test', 'tok', transport=httpx.MockTransport(b.handler))\n"
        "class Hang:\n"
        "    def run(self, s, t): threading.Event().wait()\n"
        "r = RealRunner(api, ActionLog(lambda x: None), 'm', lambda m, c: Hang(), git=FakeCheckoutGit(),\n"
        "               timeout_seconds=0.3, timeout_grace_seconds=0.0, kill_agent=lambda m: 0)\n"
        "print(r.run('fp1', '42'))\n"
    )
    done = subprocess.run([sys.executable, "-c", code], cwd=PACKAGE_ROOT, capture_output=True, text=True,
                          timeout=30, env={**os.environ, "PYTHONPATH": os.pathsep.join([PACKAGE_ROOT, PACKAGE_ROOT + "/tests"])})
    assert done.stdout.strip() == "error", done.stderr  # and it exited instead of hanging at shutdown


# -- S6: failure reason and redaction --------------------------------------------

def test_s6_a_session_exception_is_logged_by_type_name_only():
    class Odd(Exception):
        pass

    def behaviour(s):
        raise Odd("token PLANTED-LEAK in the message")

    runner, lines, _ = make_runner(behaviour)
    assert runner.run("fp1", "42") == "error"
    reasons = [e["reason"] for e in events(lines) if e["event"] == "run_failed"]
    assert reasons == ["agent_session_failed:Odd"]
    assert "PLANTED-LEAK" not in "\n".join(lines)


def b64(text):
    return base64.b64encode(text.encode()).decode()


def test_s6_every_known_secret_form_is_redacted_from_explanation_and_pull_request():
    secret = "ghp_PLANTEDsecretvalue123"
    forms = [secret, b64(secret), b64(f"x-access-token:{secret}")]
    explanation = " | ".join(f"form{i}={f}" for i, f in enumerate(forms))
    runner, lines, _ = make_runner(lambda s: AgentResult("no_change", MODEL, explanation=explanation),
                                   secrets=[secret])
    assert runner.run("fp1", "42") == "no_change"
    blob = "\n".join(lines)
    for form in forms:
        assert form not in blob
    assert blob.count("[REDACTED]") == 3

    url = f"https://pr.example/{secret}"
    runner, lines, _ = make_runner(
        lambda s: AgentResult("pull_request_opened", MODEL, pull_request=url), secrets=[secret])
    assert runner.run("fp1", "42") == "pull_request_opened"  # no repo configured: the URL is not validated
    assert secret not in "\n".join(lines)


def test_s6_redact_leaves_ordinary_text_and_short_secrets_alone():
    assert redact("nothing to hide", ["ghp_longsecretvalue"]) == "nothing to hide"
    assert redact("abc tok abc", ["tok"]) == "abc tok abc"  # too short to redact safely
    assert redact(None, ["ghp_longsecretvalue"]) is None
