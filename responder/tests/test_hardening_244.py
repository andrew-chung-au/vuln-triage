"""#244 pre-drill hardening: each finding reproduced first with a failing test, then fixed.

B1 (env scrub), S1 (branch cleanup owns only its own branch), S4 (anchored result
regex), S5 (branch client re-checks the name). No SDK, no key, no network.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest

from vt_responder.actlog import ActionLog
from vt_responder.api_client import ResponderApi
from vt_responder.fakes import FakeBranchClient
from vt_responder.github_client import GitHubRestBranches
from vt_responder.real_runner import AgentResult, RealRunner
from vt_responder.sdk_session import build_options, parse_result

from conftest import FakeBackend
from test_real_runner_isolation import BRANCH, MODEL, FakeCheckoutGit, Session, events
from test_sdk_session import KEY, TOKEN, FakeSdk, make_ctx

pytestmark = pytest.mark.unit

RESPONDER_SECRETS = {
    "RESPONDER_API_TOKEN": "PLANTED-RESPONDER-API-TOKEN",
    "RESPONDER_WEBHOOK_SECRET": "PLANTED-RESPONDER-WEBHOOK-SECRET",
    "RESPONDER_GITHUB_TOKEN": "PLANTED-RESPONDER-GITHUB-TOKEN",
}


# -- B1: the agent's subprocess environment carries no responder secret --------

def agent_env(monkeypatch, tmp_path, **extra):
    """The environment the SDK gives the CLI: ``{**os.environ, **options.env}`` (subprocess_cli.py)."""
    for name, value in {**RESPONDER_SECRETS, **extra}.items():
        monkeypatch.setenv(name, value)
    opts = build_options(FakeSdk([]), model=MODEL, system_prompt="s", ctx=make_ctx(tmp_path),
                         api_key=KEY, github_token=TOKEN).kwargs
    return {**os.environ, **opts["env"]}


def test_b1_no_responder_secret_is_non_empty_in_the_agent_env(monkeypatch, tmp_path):
    env = agent_env(monkeypatch, tmp_path, RESPONDER_LLM_KEY="PLANTED-LLM-KEY", RESPONDER_ANYTHING="x")
    for name in RESPONDER_SECRETS:
        assert env[name] == "", name
    assert not [k for k, v in env.items() if k.startswith("RESPONDER_") and v]


def test_b1_only_an_allowlist_of_the_parent_environment_survives(monkeypatch, tmp_path):
    env = agent_env(monkeypatch, tmp_path, AWS_SECRET_ACCESS_KEY="PLANTED-AWS", DATABASE_URL="postgres://u:p@h/d",
                    GITHUB_READ_TOKEN="PLANTED-READ", MAIL_SMTP_PASSWORD="PLANTED-MAIL")
    for name in ("AWS_SECRET_ACCESS_KEY", "DATABASE_URL", "GITHUB_READ_TOKEN", "MAIL_SMTP_PASSWORD"):
        assert env[name] == "", name


def test_b1_the_model_key_and_git_credentials_reach_the_cli(monkeypatch, tmp_path):
    env = agent_env(monkeypatch, tmp_path)
    assert env["ANTHROPIC_API_KEY"] == KEY  # the CLI needs it
    # LIMIT (see _docs/responder-security-limits.md): the policy lets the agent run
    # `git push` and `gh pr create` through its Bash tool, and the SDK gives every Bash
    # child the CLI's environment, so these cannot be scoped to the runner's own calls.
    assert env["GH_TOKEN"] == TOKEN
    assert env["GIT_CONFIG_VALUE_0"].startswith("AUTHORIZATION: basic ")


def test_b1_the_runners_own_git_call_gets_the_credential_but_not_the_other_secrets(monkeypatch):
    from vt_responder.checkout import SubprocessGit

    monkeypatch.setenv("RESPONDER_API_TOKEN", "PLANTED-RESPONDER-API-TOKEN")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "PLANTED-ANTHROPIC")
    seen = {}

    def fake_run(argv, **kwargs):
        seen.update(kwargs["env"])
        import subprocess
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr("vt_responder.checkout.subprocess.run", fake_run)
    SubprocessGit("o/r", "TOK123").is_clean(Path("."))
    assert "GIT_CONFIG_VALUE_0" in seen  # the git credential, for the runner's own calls
    assert "RESPONDER_API_TOKEN" not in seen and "ANTHROPIC_API_KEY" not in seen


# -- S1: cleanup deletes only a branch this run created ------------------------

def runner_for(behaviour, branches, *, lines=None):
    backend = FakeBackend()
    backend.add_finding("42", ["failed"])
    api = ResponderApi("http://backend.test", "tok", transport=httpx.MockTransport(backend.handler))
    lines = [] if lines is None else lines
    runner = RealRunner(api, ActionLog(lines.append), MODEL, lambda m, ctx: Session(behaviour),
                        git=FakeCheckoutGit(), branches=branches, timeout_seconds=5, timeout_grace_seconds=0.0)
    return runner, lines


def test_s1_a_branch_created_by_a_failed_run_is_deleted():
    branches = FakeBranchClient()

    def behaviour(s):
        branches.push(BRANCH)  # the agent pushed, then failed
        return AgentResult("error", MODEL)

    runner, lines = runner_for(behaviour, branches)
    assert runner.run("fp1", "42") == "error"
    assert branches.deleted == [BRANCH]
    assert any(e["event"] == "branch_deleted" for e in events(lines))


@pytest.mark.parametrize("result", [AgentResult("error", MODEL),
                                    AgentResult("no_change", MODEL, explanation="not reproducible")])
def test_s1_a_preexisting_branch_with_an_open_pr_is_not_deleted(result):
    branches = FakeBranchClient({BRANCH})  # an earlier run's PR is open on it
    runner, lines = runner_for(lambda s: result, branches)
    runner.run("fp1", "42")
    assert branches.deleted == [] and BRANCH in branches.branches
    preserved = [e for e in events(lines) if e["event"] == "branch_preserved"]
    assert preserved and preserved[0]["branch"] == BRANCH


def test_s1_a_preexisting_branch_the_run_pushed_to_is_deleted_only_when_its_sha_changed():
    branches = FakeBranchClient({BRANCH})

    def pushed(s):
        branches.push(BRANCH)  # new commit on the existing branch: the SHA changes
        return AgentResult("error", MODEL)

    runner, lines = runner_for(pushed, branches)
    runner.run("fp1", "42")
    assert branches.deleted == [BRANCH]

    unchanged = FakeBranchClient({BRANCH})
    runner, lines = runner_for(lambda s: AgentResult("error", MODEL), unchanged)
    runner.run("fp1", "42")
    assert unchanged.deleted == []


def test_s1_if_the_branch_cannot_be_inspected_beforehand_it_is_never_deleted():
    class Blind(FakeBranchClient):
        def get_branch_sha(self, branch):
            raise RuntimeError("network down")

    branches = Blind({BRANCH})
    runner, lines = runner_for(lambda s: AgentResult("error", MODEL), branches)
    assert runner.run("fp1", "42") == "error"
    assert branches.deleted == []
    assert any(e["event"] == "branch_preserved" for e in events(lines))


# -- S4: the reported URL is anchored and must be this run's pull request ------

@pytest.mark.parametrize("text", [
    "RESULT: PULL_REQUEST https://github.com/o/r/pull/12abc",
    "RESULT: PULL_REQUEST https://github.com/o/r/pull/12/files",
    "RESULT: PULL_REQUEST https://github.com/o/r/pull/12?x=1",
    "RESULT: PULL_REQUEST see https://github.com/o/r/pull/12",
    "RESULT: PULL_REQUEST https://github.com/o/r/pull/",
])
def test_s4_the_result_regex_is_anchored(text):
    assert parse_result(text, MODEL).outcome == "error"


def test_s4_a_url_followed_by_words_still_parses():
    out = parse_result("RESULT: PULL_REQUEST https://github.com/o/r/pull/12 fixes the retry", MODEL)
    assert out.pull_request == "https://github.com/o/r/pull/12"


def pr(number, *, ref=BRANCH, repo="owner/repo"):
    return {"number": number, "state": "open", "head": {"ref": ref, "repo": None if repo is None else {"full_name": repo}}}


def pr_runner(branches, url="https://github.com/owner/repo/pull/7"):
    backend = FakeBackend()
    backend.add_finding("42", ["failed"])
    api = ResponderApi("http://backend.test", "tok", transport=httpx.MockTransport(backend.handler))
    lines: list[str] = []
    runner = RealRunner(api, ActionLog(lines.append), MODEL,
                        lambda m, ctx: Session(lambda s: AgentResult("pull_request_opened", MODEL, pull_request=url)),
                        git=FakeCheckoutGit(), branches=branches, timeout_seconds=5, timeout_grace_seconds=0.0,
                        repo="owner/repo")
    return runner, lines


def test_s4_this_runs_pull_request_is_accepted():
    branches = FakeBranchClient(pulls={7: pr(7)})
    runner, lines = pr_runner(branches)
    assert runner.run("fp1", "42") == "pull_request_opened"


@pytest.mark.parametrize("pulls,why", [
    ({}, "pull_request_unreadable"),  # no such PR
    ({7: pr(7, ref="responder/other")}, "pull_request_not_this_runs"),  # another run's branch
    ({7: pr(7, ref="main")}, "pull_request_not_this_runs"),
    ({7: pr(7, repo="fork-owner/repo")}, "pull_request_not_this_runs"),  # a fork
    ({7: pr(7, repo=None)}, "pull_request_not_this_runs"),  # fork deleted
])
def test_s4_any_other_pull_request_is_a_failed_run(pulls, why):
    branches = FakeBranchClient(pulls=pulls)
    runner, lines = pr_runner(branches)
    assert runner.run("fp1", "42") == "error"
    assert [e["reason"] for e in events(lines) if e["event"] == "run_failed"] == [why]


def test_s4_a_failed_pull_request_check_cleans_up_a_branch_this_run_created():
    branches = FakeBranchClient(pulls={7: pr(7, ref="responder/other")})
    backend = FakeBackend()
    backend.add_finding("42", ["failed"])
    api = ResponderApi("http://backend.test", "tok", transport=httpx.MockTransport(backend.handler))

    def behaviour(s):
        branches.push(BRANCH)
        return AgentResult("pull_request_opened", MODEL, pull_request="https://github.com/owner/repo/pull/7")

    runner = RealRunner(api, ActionLog(lambda x: None), MODEL, lambda m, ctx: Session(behaviour),
                        git=FakeCheckoutGit(), branches=branches, timeout_seconds=5, timeout_grace_seconds=0.0,
                        repo="owner/repo")
    assert runner.run("fp1", "42") == "error"
    assert branches.deleted == [BRANCH]


# -- S5: the REST branch client re-checks what it is asked to delete -----------

@pytest.mark.parametrize("branch", ["../main", "responder/../main", "main", "responder/", "responder/a/b",
                                    "responder/a b", "responder/x\n", "responder/" + "x" * 65])
def test_s5_the_rest_client_refuses_names_that_are_not_responder_branches(branch):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={})

    client = GitHubRestBranches("o/r", "T", transport=httpx.MockTransport(handler))
    with pytest.raises(ValueError):
        client.delete_branch_if_exists(branch)
    with pytest.raises(ValueError):
        client.get_branch_sha(branch)
    assert seen == []


def test_s5_the_rest_client_reads_a_sha_and_a_pull_request():
    def handler(request):
        if request.url.path == "/repos/o/r/git/ref/heads/responder/fp1":
            return httpx.Response(200, json={"object": {"sha": "abc123"}})
        if request.url.path == "/repos/o/r/pulls/7":
            return httpx.Response(200, json={"number": 7})
        return httpx.Response(404, json={})

    client = GitHubRestBranches("o/r", "T", transport=httpx.MockTransport(handler))
    assert client.get_branch_sha("responder/fp1") == "abc123"
    assert client.get_branch_sha("responder/none") is None
    assert client.get_pull_request(7) == {"number": 7}
    assert client.get_pull_request(8) is None
