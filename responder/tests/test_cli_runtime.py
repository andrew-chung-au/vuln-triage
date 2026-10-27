"""#260: the headless `claude -p` runtime, driven by a FAKE `claude` executable (no login, no network, no model).

Covers: configuration, the start-up login preflight, the CLI's environment (no API key, no git token, no
responder secret), the argv, the result and failure parsing, the time limit and process-group kill, and
the whole runner flow with the runner (not the agent) pushing and opening the pull request.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import httpx
import pytest

from vt_responder.actlog import ActionLog
from vt_responder.api_client import ResponderApi
from vt_responder.app import create_app
from vt_responder.cli_session import CliSession, parse_output, preflight
from vt_responder.config import ConfigError, Settings
from vt_responder.envscrub import CLI_FORBIDDEN, cli_env
from vt_responder.fakes import FakeBranchClient
from vt_responder.prompt import CLI_SYSTEM_PROMPT, build_cli_task
from vt_responder.publisher import GitPublisher
from vt_responder.real_runner import AgentResult, RealRunner, RunContext

import fake_claude
from conftest import FakeBackend, make_settings
from fake_claude import calls, host_env, install, is_dead, result_json
from test_publisher import BASE, SQUASHED, FakePublishGit
from test_real_runner_isolation import BRANCH, MODEL, FakeCheckoutGit, events

pytestmark = pytest.mark.unit

CLI_ENV = {"RESPONDER_MODE": "real", "RESPONDER_WEBHOOK_SECRET": "w", "RESPONDER_API_TOKEN": "t",
           "RESPONDER_MODEL": MODEL, "RESPONDER_GITHUB_TOKEN": "g", "RESPONDER_GITHUB_REPO": "o/r"}


# -- configuration -------------------------------------------------------------------------------

def test_the_cli_runtime_is_the_real_mode_default_and_needs_no_api_key():
    settings = Settings.from_env(CLI_ENV)
    assert settings.runtime == "cli" and settings.anthropic_api_key == ""
    assert Settings.from_env({**CLI_ENV, "RESPONDER_RUNTIME": ""}).runtime == "cli"  # an empty .env entry
    assert Settings.from_env({**CLI_ENV, "RESPONDER_RUNTIME": "cli"}).runtime == "cli"


def test_an_api_key_in_the_environment_is_never_held_by_the_cli_runtime():
    settings = Settings.from_env({**CLI_ENV, "ANTHROPIC_API_KEY": "PLANTED-ANTHROPIC-KEY"})
    assert settings.anthropic_api_key == "" and "PLANTED" not in repr(settings)


def test_the_sdk_runtime_still_requires_the_api_key():
    sdk = {**CLI_ENV, "RESPONDER_RUNTIME": "sdk"}
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        Settings.from_env(sdk)
    assert Settings.from_env({**sdk, "ANTHROPIC_API_KEY": "k"}).anthropic_api_key == "k"


@pytest.mark.parametrize("value", ["CLI", "claude", "api", "sdk2", "cli,sdk", "0"])
def test_an_unknown_runtime_is_refused(value):
    with pytest.raises(ConfigError, match="RESPONDER_RUNTIME"):
        Settings.from_env({**CLI_ENV, "RESPONDER_RUNTIME": value})


@pytest.mark.parametrize("missing", ["RESPONDER_MODEL", "RESPONDER_WEBHOOK_SECRET", "RESPONDER_API_TOKEN",
                                     "RESPONDER_GITHUB_TOKEN", "RESPONDER_GITHUB_REPO"])
def test_the_cli_runtime_still_requires_model_secrets_token_and_repo(missing):
    env = {k: v for k, v in CLI_ENV.items() if k != missing}
    with pytest.raises(ConfigError, match=missing):
        Settings.from_env(env)


@pytest.mark.parametrize("marker", [{"CI": "true"}, {"GITHUB_ACTIONS": "1"}, {"PYTEST_CURRENT_TEST": "x"},
                                    {"DEPLOYMENT_ENVIRONMENT": "test"}])
def test_real_mode_with_the_cli_runtime_is_still_refused_in_ci_and_test(marker):
    with pytest.raises(ConfigError, match="stub"):
        Settings.from_env({**CLI_ENV, **marker})


def test_the_commit_limit_has_a_default_and_rejects_bad_values():
    assert Settings.from_env(CLI_ENV).max_commits == 3
    assert Settings.from_env({**CLI_ENV, "RESPONDER_MAX_COMMITS": "1"}).max_commits == 1
    assert Settings.from_env({**CLI_ENV, "RESPONDER_MAX_COMMITS": ""}).max_commits == 3
    for bad in ("0", "-1", "x"):
        with pytest.raises(ConfigError):
            Settings.from_env({**CLI_ENV, "RESPONDER_MAX_COMMITS": bad})


def test_stub_mode_ignores_the_runtime_except_to_refuse_a_typo():
    stub = {"RESPONDER_MODE": "stub", "RESPONDER_WEBHOOK_SECRET": "s", "RESPONDER_API_TOKEN": "t"}
    assert Settings.from_env(stub).mode == "stub"
    with pytest.raises(ConfigError):
        Settings.from_env({**stub, "RESPONDER_RUNTIME": "nope"})


# -- the start-up preflight ------------------------------------------------------------------------

def test_preflight_passes_with_a_logged_in_claude_and_checks_it_without_the_api_key(tmp_path):
    bin_dir = install(tmp_path)
    assert preflight(host_env(bin_dir)) == "claude.ai"
    status = calls(tmp_path, "status")[0]["env"]
    assert "ANTHROPIC_API_KEY" not in status and "ANTHROPIC_AUTH_TOKEN" not in status  # same scrub as a run
    assert calls(tmp_path, "run") == []  # no model call, no run


def test_preflight_accepts_a_long_lived_login_token(tmp_path):
    assert preflight(host_env(install(tmp_path, method="oauth_token"))) == "oauth_token"


def test_preflight_fails_clearly_when_claude_is_not_installed(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ConfigError, match="not on PATH"):
        preflight({"PATH": str(empty), "HOME": "/home/owner"})


def test_preflight_fails_clearly_when_claude_is_not_logged_in(tmp_path):
    with pytest.raises(ConfigError, match="not logged in"):
        preflight(host_env(install(tmp_path, login_exit=1)))


def test_preflight_refuses_a_status_that_says_logged_out_even_with_exit_zero(tmp_path):
    with pytest.raises(ConfigError, match="not logged in"):
        preflight(host_env(install(tmp_path, logged_in=False)))


@pytest.mark.parametrize("method", ["api_key", "api_key_helper", "third_party", "none", "weird method!"])
def test_preflight_refuses_a_login_that_is_not_a_subscription_login(tmp_path, method):
    with pytest.raises(ConfigError, match="not a subscription login"):
        preflight(host_env(install(tmp_path, method=method)))


def test_preflight_refuses_a_claude_that_lacks_a_flag_the_run_uses(tmp_path):
    with pytest.raises(ConfigError, match="--safe-mode"):
        preflight(host_env(install(tmp_path, help_missing=("--safe-mode",))))


def test_create_app_fails_start_up_without_a_logged_in_claude(tmp_path, monkeypatch):
    settings = make_settings(tmp_path, mode="real", model=MODEL, repo="o/r", github_token="t", runtime="cli")
    monkeypatch.setenv("PATH", str(tmp_path))  # no claude on it
    with pytest.raises(ConfigError, match="not on PATH"):
        create_app(settings)
    bin_dir = install(tmp_path, login_exit=1)
    monkeypatch.setenv("PATH", str(bin_dir))
    with pytest.raises(ConfigError, match="not logged in"):
        create_app(settings)


def test_create_app_starts_with_a_logged_in_claude_and_never_runs_it(tmp_path, monkeypatch):
    bin_dir = install(tmp_path)
    monkeypatch.setenv("PATH", str(bin_dir))
    settings = make_settings(tmp_path, mode="real", model=MODEL, repo="o/r", github_token="t", runtime="cli")
    assert create_app(settings) is not None
    assert calls(tmp_path, "run") == []


def test_the_sdk_runtime_does_not_run_the_cli_preflight(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))  # no claude at all
    settings = make_settings(tmp_path, mode="real", model=MODEL, repo="o/r", github_token="t",
                             anthropic_api_key="k", runtime="sdk")
    assert create_app(settings) is not None


# -- the environment and argv of the CLI ------------------------------------------------------------

def make_ctx(tmp_path: Path, *, timeout=20, turns=7, marker="marker-abc") -> RunContext:
    checkout = tmp_path / "checkout"
    checkout.mkdir(exist_ok=True)
    return RunContext("fp1", checkout, None, ActionLog(lambda line: None), turns, timeout, run_marker=marker)


RESULT_FIXED = result_json("looked at it\nRESULT: FIXED the retry loop swallowed the error")


def run_session(tmp_path, *, environ=None, **fake):
    bin_dir = install(tmp_path, **({"stdout": RESULT_FIXED} | fake))
    ctx = make_ctx(tmp_path)
    session = CliSession(MODEL, ctx, environ=environ if environ is not None else host_env(bin_dir))
    return session.run(CLI_SYSTEM_PROMPT, build_cli_task("fp1", "42")), ctx


def test_no_api_key_secret_or_git_token_reaches_the_cli(tmp_path):
    result, _ = run_session(tmp_path)
    assert result.outcome == "fixed"
    env = calls(tmp_path, "run")[0]["env"]
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "GH_TOKEN", "GITHUB_TOKEN", "RESPONDER_GITHUB_TOKEN",
                 "RESPONDER_API_TOKEN", "RESPONDER_WEBHOOK_SECRET", "GIT_CONFIG_VALUE_0", "AWS_SECRET_ACCESS_KEY"):
        assert name not in env, name
    assert "PLANTED" not in json.dumps(env)  # not under another name either
    assert not [k for k in env if k.startswith(("RESPONDER_", "GIT_CONFIG"))]


def test_the_cli_keeps_home_path_and_the_login_variables(tmp_path):
    bin_dir = install(tmp_path, stdout=RESULT_FIXED)
    environ = host_env(bin_dir, CLAUDE_CONFIG_DIR="/home/owner/.claude-alt", CLAUDE_CODE_OAUTH_TOKEN="login-token")
    CliSession(MODEL, make_ctx(tmp_path), environ=environ).run("s", "t")
    env = calls(tmp_path, "run")[0]["env"]
    assert env["HOME"] == "/home/owner" and str(bin_dir) in env["PATH"]
    assert env["CLAUDE_CONFIG_DIR"] == "/home/owner/.claude-alt" and env["CLAUDE_CODE_OAUTH_TOKEN"] == "login-token"
    assert env["VT_RUN_MARKER"] == "marker-abc"  # lets the runner stop this run's processes
    assert env["GIT_AUTHOR_NAME"] and env["GIT_COMMITTER_EMAIL"] and env["GIT_TERMINAL_PROMPT"] == "0"


def test_cli_env_removes_forbidden_names_even_if_asked_for_in_extra():
    env = cli_env({"PATH": "/bin", "HOME": "/h", "ANTHROPIC_API_KEY": "k"},
                  {"ANTHROPIC_AUTH_TOKEN": "t", "GH_TOKEN": "g", "X": "1"})
    assert env == {"PATH": "/bin", "HOME": "/h", "X": "1"}
    assert {"ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"} <= CLI_FORBIDDEN


def test_cli_env_drops_everything_not_allowlisted_and_login_vars_only_when_named():
    env = cli_env({"PATH": "/bin", "DATABASE_URL": "postgres://u:p@h/d", "CLAUDE_CONFIG_DIR": "/c", "LC_ALL": "C"})
    assert env == {"PATH": "/bin", "CLAUDE_CONFIG_DIR": "/c", "LC_ALL": "C"}


def test_the_argv_uses_the_verified_flags_and_sends_the_task_on_stdin(tmp_path):
    result, ctx = run_session(tmp_path)
    run = calls(tmp_path, "run")[0]
    argv, task = run["argv"], build_cli_task("fp1", "42")
    assert "-p" in argv and argv[argv.index("--model") + 1] == MODEL
    assert argv[argv.index("--max-turns") + 1] == "7"
    assert argv[argv.index("--output-format") + 1] == "json"
    assert argv[argv.index("--permission-mode") + 1] == "dontAsk"
    assert "--no-session-persistence" in argv and "--safe-mode" in argv
    assert argv[argv.index("--append-system-prompt") + 1] == CLI_SYSTEM_PROMPT
    assert run["stdin"] == task and task not in argv  # not an argument a variadic flag could swallow
    for flag in ("--tools", "--allowedTools", "--disallowedTools"):
        assert "," in argv[argv.index(flag) + 1] and not argv[argv.index(flag) + 1].startswith("--")
    # never the flags that would skip permissions, use an API key, or spend dollars
    for bad in ("--dangerously-skip-permissions", "--allow-dangerously-skip-permissions", "--bare",
                "--max-budget-usd", "--permission-mode=bypassPermissions"):
        assert bad not in argv
    assert "bypassPermissions" not in argv and "acceptEdits" not in argv


def test_the_run_starts_in_the_checkout_in_its_own_process_group_and_leaves_no_file_behind(tmp_path, monkeypatch):
    # An isolated temp root, so another process's `vt-cli-*` directory in the shared /tmp cannot fail the test.
    private_tmp = tmp_path / "private-tmp"
    private_tmp.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(private_tmp))
    result, ctx = run_session(tmp_path)
    run = calls(tmp_path, "run")[0]
    assert Path(run["cwd"]).resolve() == ctx.checkout.resolve()
    assert run["pgid"] == run["pid"]  # its own group, so killpg never touches the responder
    assert list(ctx.checkout.iterdir()) == []  # the output went to a temp directory, not the checkout
    assert list(private_tmp.iterdir()) == []  # nothing left under the temp root the run used


# -- result parsing and failures ---------------------------------------------------------------------

@pytest.mark.parametrize("text,outcome,explanation", [
    ("RESULT: FIXED the retry loop swallowed the error", "fixed", "the retry loop swallowed the error"),
    ("notes\nRESULT: FALSE_POSITIVE nothing failed, the job was retried", "no_change", "nothing failed, the job was retried"),
    ("RESULT: FALSE_POSITIVE", "no_change", None),
    ("RESULT: FALSE_POSITIVE x\nRESULT: FIXED y", "fixed", "y"),  # the last line wins
])
def test_the_result_line_is_parsed(text, outcome, explanation):
    parsed = parse_output(result_json(text), MODEL)
    assert (parsed.outcome, parsed.explanation) == (outcome, explanation)
    assert parsed.model == "claude-sonnet-5-5"


@pytest.mark.parametrize("body,reason", [
    ("RESULT: ESCALATE I cannot tell", "agent_escalated"),
    ("I fixed it, trust me", "result_line_missing"),
    ("RESULT: PULL_REQUEST https://github.com/o/r/pull/1", "result_line_missing"),  # the SDK form is not accepted
    ("RESULT: FIXED", None),  # a FIXED with no summary is still fixed
    ("", "result_line_missing"),
    ("  RESULT: FIXED indented", "result_line_missing"),
])
def test_other_results_are_failed_runs_with_a_reason(body, reason):
    parsed = parse_output(result_json(body), MODEL)
    if reason is None:
        assert parsed.outcome == "fixed"
    else:
        assert (parsed.outcome, parsed.reason) == ("error", reason)


@pytest.mark.parametrize("text,reason", [
    ("not json", "output_unparseable"), ("", "output_unparseable"), ("[1, 2]", "output_unparseable"),
    ("null", "output_unparseable"), ("{", "output_unparseable"),
    (result_json("RESULT: FIXED x", is_error=True), "agent_cli_error"),
    (result_json("RESULT: FIXED x", subtype="error_during_execution"), "agent_cli_error"),
    (result_json("", subtype="error_max_turns", is_error=True), "max_turns"),
    (result_json("You've hit your session limit", is_error=True), "plan_usage_limit"),
    (result_json("Claude usage limit reached", is_error=True), "plan_usage_limit"),
])
def test_unparseable_or_error_output_is_a_failed_run(text, reason):
    parsed = parse_output(text, MODEL)
    assert (parsed.outcome, parsed.reason) == ("error", reason)


@pytest.mark.parametrize("body,reason", [
    ("```\nRESULT: FIXED quoted from a file\n```", "result_line_missing"),
    ("```\nRESULT: FIXED quoted\n```\nRESULT: ESCALATE real", "agent_escalated"),
    ("```text\nRESULT: FIXED quoted\nmore", "result_line_missing"),  # an unclosed fence runs to the end
    ("~~~\nRESULT: FIXED quoted\n~~~", "result_line_missing"),
    ("  ```\nRESULT: FIXED quoted\n  ```", "result_line_missing"),
    # a longer fence is closed only by a fence at least as long, with nothing but spaces after it
    ("````\n```\nRESULT: FIXED quoted\n````", "result_line_missing"),
    ("````\n```\n```\nRESULT: FIXED quoted\n````", "result_line_missing"),
    ("~~~~\n~~~\nRESULT: FIXED quoted\n~~~~", "result_line_missing"),
    ("```\n```text\nRESULT: FIXED quoted\n```", "result_line_missing"),  # an info string does not close a fence
    ("```\n~~~\nRESULT: FIXED quoted\n```", "result_line_missing"),  # another character does not close it
])
def test_a_result_line_inside_a_code_fence_does_not_count(body, reason):
    parsed = parse_output(result_json(body), MODEL)
    assert (parsed.outcome, parsed.reason) == ("error", reason)


def test_a_result_line_after_a_closed_code_fence_counts():
    parsed = parse_output(result_json("```\ncode\n```\nRESULT: FIXED after the fence"), MODEL)
    assert (parsed.outcome, parsed.explanation) == ("fixed", "after the fence")


@pytest.mark.parametrize("body", [
    "````\n```\ncode\n```\n````\nRESULT: FIXED after the fence",
    "```\ncode\n````\nRESULT: FIXED after the fence",  # a longer closing fence closes too
    "```\ncode\n```   \nRESULT: FIXED after the fence",
])
def test_a_result_line_after_a_properly_closed_fence_counts(body):
    parsed = parse_output(result_json(body), MODEL)
    assert (parsed.outcome, parsed.explanation) == ("fixed", "after the fence")


def test_output_over_the_size_cap_is_a_failed_run_not_unparseable_text(tmp_path, monkeypatch):
    monkeypatch.setattr("vt_responder.cli_session._MAX_OUTPUT_BYTES", 1000)
    result, _ = run_session(tmp_path, stdout=result_json("RESULT: FIXED " + "y" * 2000))
    assert (result.outcome, result.reason) == ("error", "output_too_large")


def test_a_run_that_floods_its_output_is_killed_while_running(tmp_path, monkeypatch):
    import time

    monkeypatch.setattr("vt_responder.cli_session._MAX_OUTPUT_BYTES", 1000)
    started = time.monotonic()
    result, _ = run_session(tmp_path, flood=50_000, sleep=30)
    assert (result.outcome, result.reason) == ("error", "output_too_large")
    assert time.monotonic() - started < 15  # killed on the cap, not after the 30 s sleep


def test_an_unusable_served_model_name_falls_back_to_the_configured_model():
    out = parse_output(result_json("RESULT: FIXED x", modelUsage={"x" * 200: {}}), MODEL)
    assert out.model == MODEL


@pytest.mark.parametrize("fake,reason", [
    ({"exit": 1, "stdout": ""}, "cli_exit_nonzero"),
    ({"exit": 2, "stdout": RESULT_FIXED}, "cli_exit_nonzero"),  # a non-zero exit is never a success
    ({"exit": 1, "stdout": result_json("You've hit your weekly limit", is_error=True)}, "plan_usage_limit"),
    ({"exit": 1, "stdout": "", "stderr": "Claude usage limit reached. Your limit will reset at 5pm"}, "plan_usage_limit"),
    ({"exit": 1, "stdout": result_json("", subtype="error_max_turns", is_error=True)}, "max_turns"),
    ({"exit": 0, "stdout": "plain text"}, "output_unparseable"),
])
def test_a_failing_cli_run_is_a_failed_run(tmp_path, fake, reason):
    result, _ = run_session(tmp_path, **fake)
    assert (result.outcome, result.reason) == ("error", reason)


def test_agent_text_and_stderr_never_reach_the_failure_reason(tmp_path):
    result, _ = run_session(tmp_path, exit=1, stdout="", stderr="token PLANTED-LEAK in the message")
    assert "PLANTED-LEAK" not in repr(result)


def test_a_missing_binary_raises_a_failed_session(tmp_path):
    session = CliSession(MODEL, make_ctx(tmp_path), environ={"PATH": str(tmp_path), "HOME": "/h"})
    with pytest.raises(FileNotFoundError):
        session.run("s", "t")


# -- the time limit and the process-group kill -------------------------------------------------------

def test_the_time_limit_kills_the_whole_process_group(tmp_path):
    bin_dir = install(tmp_path, sleep=30, spawn_child=True)
    session = CliSession(MODEL, make_ctx(tmp_path, timeout=1), environ=host_env(bin_dir))
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        session.run("s", "t")
    assert time.monotonic() - started < 15
    run = calls(tmp_path, "run")[0]
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not (is_dead(run["pid"]) and is_dead(run["child_pid"])):
        time.sleep(0.05)
    assert is_dead(run["pid"]) and is_dead(run["child_pid"])  # the CLI and what it started


# -- the whole runner flow: the RUNNER pushes and opens the pull request --------------------------------

def runner_rig(tmp_path, *, stdout=RESULT_FIXED, publish_git=None, branches=None, secrets=("ghp_PLANTEDsecretvalue123",),
               timeout=20, **fake):
    bin_dir = install(tmp_path, stdout=stdout, **fake)
    backend = FakeBackend()
    backend.add_finding("42", ["failed"])
    api = ResponderApi("http://backend.test", "tok", transport=httpx.MockTransport(backend.handler))
    lines: list[str] = []
    branches = branches if branches is not None else FakeBranchClient()
    pgit = publish_git if publish_git is not None else FakePublishGit(branches=branches)
    publisher = GitPublisher(pgit, branches, secrets=list(secrets), max_commits=3)
    sessions: list[RunContext] = []

    def make(model, ctx):
        sessions.append(ctx)
        return CliSession(model, ctx, environ=host_env(bin_dir))

    runner = RealRunner(api, ActionLog(lines.append), MODEL, make, git=FakeCheckoutGit(), branches=branches,
                        timeout_seconds=timeout, timeout_grace_seconds=0.0, repo="owner/repo",
                        publisher=publisher, secrets=list(secrets), system_prompt=CLI_SYSTEM_PROMPT,
                        task_builder=build_cli_task, max_turns=7)
    return runner, lines, branches, pgit, sessions


def test_fixed_the_runner_pushes_and_opens_the_pull_request_and_applies_the_s4_check(tmp_path):
    runner, lines, branches, pgit, _ = runner_rig(tmp_path)
    assert runner.run("fp1", "42") == "pull_request_opened"
    assert pgit.pushed == [(SQUASHED, BRANCH)]  # the runner's one commit, not the agent's head
    assert branches.created and branches.created[0]["head"] == BRANCH
    opened = [e for e in events(lines) if e["event"] == "pull_request_opened"]
    assert opened and opened[0]["pull_request"] == "https://github.com/owner/repo/pull/100"
    assert any(e["event"] == "branch_pushed" and e["branch"] == BRANCH for e in events(lines))
    assert branches.deleted == []  # the branch stays: a PR is open on it
    assert "the retry loop swallowed the error" in branches.created[0]["body"]  # the agent's one-line summary


def test_the_agent_text_in_the_pull_request_body_is_redacted(tmp_path):
    text = "RESULT: FIXED the token ghp_PLANTEDsecretvalue123 leaked in a log"
    runner, lines, branches, *_ = runner_rig(tmp_path, stdout=result_json(text))
    assert runner.run("fp1", "42") == "pull_request_opened"
    assert "ghp_PLANTED" not in branches.created[0]["body"] and "[REDACTED]" in branches.created[0]["body"]


def test_false_positive_pushes_nothing_logs_the_explanation_and_leaves_no_branch(tmp_path):
    out = result_json("checked\nRESULT: FALSE_POSITIVE the job succeeded on its second attempt")
    runner, lines, branches, pgit, _ = runner_rig(tmp_path, stdout=out)
    assert runner.run("fp1", "42") == "no_change"
    assert pgit.pushed == [] and branches.created == [] and BRANCH not in branches.branches
    nc = [e for e in events(lines) if e["event"] == "no_change"]
    assert nc[-1]["explanation"] == "the job succeeded on its second attempt"  # US-15


@pytest.mark.parametrize("stdout,fake,reason", [
    (RESULT_FIXED, {"exit": 1}, "cli_exit_nonzero"),
    (result_json("You've hit your session limit", is_error=True), {"exit": 1}, "plan_usage_limit"),
    ("garbage", {}, "output_unparseable"),
    (result_json("done, no result line"), {}, "result_line_missing"),
    (result_json("RESULT: ESCALATE cannot decide"), {}, "agent_escalated"),
    (result_json("", subtype="error_max_turns", is_error=True), {"exit": 1}, "max_turns"),
])
def test_a_failed_cli_run_is_a_failed_runner_run_and_pushes_nothing(tmp_path, stdout, fake, reason):
    runner, lines, branches, pgit, sessions = runner_rig(tmp_path, stdout=stdout, **fake)
    assert runner.run("fp1", "42") == "error"
    assert [e["reason"] for e in events(lines) if e["event"] == "run_failed"] == [reason]
    assert pgit.pushed == [] and branches.created == []
    assert not sessions[0].checkout.exists()  # the checkout is removed


def test_a_refused_diff_is_a_failed_run_and_the_branch_this_run_created_is_cleaned_up(tmp_path):
    from vt_responder.publisher import Change

    branches = FakeBranchClient()
    pgit = FakePublishGit([Change("M", "100644", "100644", ".github/workflows/verify.yml")], branches=branches)
    runner, lines, branches, pgit, sessions = runner_rig(tmp_path, publish_git=pgit, branches=branches)
    assert runner.run("fp1", "42") == "error"
    assert [e["reason"] for e in events(lines) if e["event"] == "run_failed"] == ["diff_path_github_dir"]
    assert pgit.pushed == [] and branches.created == []
    assert not sessions[0].checkout.exists()


def test_a_pull_request_that_fails_after_the_push_removes_the_branch_this_run_created(tmp_path):
    branches = FakeBranchClient()
    branches.fail_create = True
    runner, lines, branches, pgit, _ = runner_rig(tmp_path, publish_git=FakePublishGit(branches=branches),
                                                  branches=branches)
    assert runner.run("fp1", "42") == "error"
    assert [e["reason"] for e in events(lines) if e["event"] == "run_failed"] == ["pull_request_create_failed"]
    assert pgit.pushed and branches.deleted == [BRANCH]  # S1: created by this run, so removed


def test_a_preexisting_branch_is_kept_when_the_run_fails_without_pushing(tmp_path):
    branches = FakeBranchClient({BRANCH})  # an earlier run's PR is open on it
    runner, lines, branches, *_ = runner_rig(tmp_path, stdout=result_json("no result line"), branches=branches)
    assert runner.run("fp1", "42") == "error"
    assert branches.deleted == [] and BRANCH in branches.branches


def test_the_time_limit_is_a_failed_run_and_the_cli_tree_is_killed_before_the_checkout_goes(tmp_path):
    runner, lines, branches, pgit, sessions = runner_rig(tmp_path, sleep=30, spawn_child=True, timeout=1)
    assert runner.run("fp1", "42") == "error"
    assert [e["reason"] for e in events(lines) if e["event"] == "run_failed"] == ["agent_timeout"]
    assert pgit.pushed == []
    run = calls(tmp_path, "run")[0]
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not (is_dead(run["pid"]) and is_dead(run["child_pid"])):
        time.sleep(0.05)
    assert is_dead(run["pid"]) and is_dead(run["child_pid"])


def test_the_run_marker_kill_is_still_called_after_a_cli_run(tmp_path):
    killed = []
    runner, lines, branches, pgit, sessions = runner_rig(tmp_path)
    runner._kill_agent = killed.append
    runner.run("fp1", "42")
    assert killed == [sessions[0].run_marker] and killed[0]


def test_no_advisory_text_or_secret_reaches_the_log_or_the_pull_request(tmp_path):
    from conftest import ADVISORY_TEXT

    runner, lines, branches, *_ = runner_rig(tmp_path)
    runner.run("fp1", "42")
    blob = "\n".join(lines) + json.dumps(branches.created)
    assert ADVISORY_TEXT not in blob and "PLANTED" not in blob


def test_the_cli_prompt_tells_the_agent_not_to_push_and_to_end_with_the_result_line():
    flat = " ".join(CLI_SYSTEM_PROMPT.split())
    for needle in ("NEVER run `git push`", "never open a pull request", "RESULT: FIXED", "RESULT: FALSE_POSITIVE",
                   "RESULT: ESCALATE", "explicit paths", "change and commit nothing",
                   "& ( ) ; < > $ { }", "a backtick", "a tab"):  # the characters a commit message may not hold
        assert needle in flat, needle
    assert "git push -u" not in flat and "gh pr create`" not in flat  # the SDK instructions are not reused
    task = build_cli_task("fp1", "42")
    assert "fp1" in task and "42" in task


def test_env_example_lists_the_runtime_names_with_no_value():
    text = (Path(__file__).resolve().parents[2] / ".env.example").read_text()
    for name in ("RESPONDER_RUNTIME", "RESPONDER_MAX_COMMITS"):
        assert f"\n{name}=\n" in text, name


def test_the_fake_claude_is_the_only_claude_the_tests_can_reach(tmp_path):
    """A guard on the test design: the fake answers --version, so nothing here needs the real CLI."""
    bin_dir = install(tmp_path)
    done = subprocess.run([str(bin_dir / "claude"), "--version"], capture_output=True, text=True, check=True)
    assert done.stdout.startswith("2.1.311") and fake_claude.SCRIPT.startswith("#!@PYTHON@")
