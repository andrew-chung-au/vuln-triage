"""#221: fresh checkout per run, bounded run, no partial branch. Fake git, fake GitHub, fake session."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import httpx
import pytest

from vt_responder.actlog import ActionLog
from vt_responder.api_client import ResponderApi
from vt_responder.checkout import CheckoutError, SubprocessGit, fresh_checkout, git_auth_env
from vt_responder.fakes import FakeBranchClient
from vt_responder.github_client import GitHubRestBranches
from vt_responder.real_runner import AgentResult, RealRunner

from conftest import FakeBackend

pytestmark = pytest.mark.unit

MODEL = "claude-sonnet-5-5"
BRANCH = "responder/fp1"


class FakeCheckoutGit:
    """Makes a real directory (so deletion is observable) but never runs git."""

    def __init__(self, clean: bool = True, fail: bool = False) -> None:
        self.clean, self.fail = clean, fail
        self.dests: list[Path] = []

    def clone(self, dest: Path) -> None:
        if self.fail:
            raise RuntimeError("clone of https://x-access-token:SEKRET@github.com failed")
        dest.mkdir(parents=True)
        (dest / "marker.txt").write_text("checkout")
        self.dests.append(dest)

    def is_clean(self, dest: Path) -> bool:
        return self.clean


class Session:
    def __init__(self, behaviour, branches: FakeBranchClient | None = None) -> None:
        self.behaviour, self.branches = behaviour, branches
        self.ctx = None

    def run(self, system_prompt, task):
        return self.behaviour(self)


def rig(tmp_path: Path, behaviour, *, git=None, branches=None, timeout=5, grace=0.0):
    backend = FakeBackend()
    backend.add_finding("42", ["failed"])
    api = ResponderApi("http://backend.test", "tok", transport=httpx.MockTransport(backend.handler))
    lines: list[str] = []
    branches = branches if branches is not None else FakeBranchClient()
    git = git if git is not None else FakeCheckoutGit()
    sessions: list[Session] = []

    def make(model, ctx):
        s = Session(behaviour)
        s.ctx = ctx
        sessions.append(s)
        return s

    runner = RealRunner(api, ActionLog(lines.append), MODEL, make, git=git, branches=branches,
                        max_turns=7, timeout_seconds=timeout, timeout_grace_seconds=grace)
    return runner, lines, git, branches, sessions


def events(lines):
    return [json.loads(x) for x in lines]


def test_each_run_gets_its_own_fresh_checkout_that_is_deleted_afterwards(tmp_path):
    seen = []

    def behaviour(s):
        seen.append((s.ctx.checkout, s.ctx.checkout.exists(), (s.ctx.checkout / "marker.txt").exists()))
        return AgentResult("no_change", MODEL, explanation="not reproducible")

    runner, lines, git, branches, sessions = rig(tmp_path, behaviour)
    assert runner.run("fp1", "42") == "no_change"
    assert runner.run("fp2", "42") == "no_change"
    (c1, exists1, marker1), (c2, _, _) = seen
    assert exists1 and marker1
    assert c1 != c2  # a new checkout per alert
    assert not c1.exists() and not c2.exists()  # deleted afterwards
    assert not c1.parent.exists()  # and so is its temporary parent directory


def rig_with_repo(behaviour, repo):
    backend = FakeBackend()
    backend.add_finding("42", ["failed"])
    api = ResponderApi("http://backend.test", "tok", transport=httpx.MockTransport(backend.handler))
    lines: list[str] = []
    # #244 S4: the reported pull request is read back and must be this run's (PR 7 here).
    branches = FakeBranchClient(pulls={7: {"head": {"ref": BRANCH, "repo": {"full_name": "owner/repo"}}}})
    runner = RealRunner(api, ActionLog(lines.append), MODEL, lambda m, ctx: Session(behaviour),
                        git=FakeCheckoutGit(), branches=branches, timeout_seconds=5,
                        timeout_grace_seconds=0.0, repo=repo)
    return runner, lines


@pytest.mark.parametrize("url", [
    "https://github.com/owner/repo/pull/7",
    "https://github.com/Owner/Repo/pull/7",
])
def test_a_pull_request_url_in_the_configured_repo_is_accepted(url):
    runner, lines = rig_with_repo(lambda s: AgentResult("pull_request_opened", MODEL, pull_request=url),
                                  "owner/repo")
    assert runner.run("fp1", "42") == "pull_request_opened"
    assert any(e["event"] == "pull_request_opened" and e["pull_request"] == url for e in events(lines))


@pytest.mark.parametrize("url", [
    "https://github.com/other/repo/pull/7",
    "https://github.com/owner/repo-evil/pull/7",
    "https://github.com/owner/repo/pull/7/files",
    "https://github.com/owner/repo/issues/7",
    "https://evil.example/owner/repo/pull/7",
    "http://github.com/owner/repo/pull/7",
    "https://github.com/owner/repo/pull/7?x=1",
])
def test_a_pull_request_url_outside_the_configured_repo_is_a_failed_run(url):
    runner, lines = rig_with_repo(lambda s: AgentResult("pull_request_opened", MODEL, pull_request=url),
                                  "owner/repo")
    assert runner.run("fp1", "42") == "error"
    blob = "\n".join(lines)
    assert "pull_request_url_invalid" in blob
    assert url not in blob  # an unvalidated URL is not echoed into the log


def test_the_session_is_handed_the_bounds_and_a_policy_for_this_fingerprint(tmp_path):
    def behaviour(s):
        assert s.ctx.max_turns == 7 and s.ctx.timeout_seconds == 5
        assert s.ctx.policy.branch == BRANCH
        return AgentResult("no_change", MODEL, explanation="x")

    runner, *_ = rig(tmp_path, behaviour)
    assert runner.run("fp1", "42") == "no_change"


def test_the_checkout_is_deleted_when_the_agent_errors(tmp_path):
    def behaviour(s):
        raise RuntimeError("boom")

    runner, lines, git, *_ = rig(tmp_path, behaviour)
    assert runner.run("fp1", "42") == "error"
    assert git.dests and not git.dests[0].exists() and not git.dests[0].parent.exists()


def test_a_dirty_checkout_refuses_to_start_the_agent(tmp_path):
    called = []
    runner, lines, git, *_ = rig(tmp_path, lambda s: called.append(1), git=FakeCheckoutGit(clean=False))
    assert runner.run("fp1", "42") == "error"
    assert called == []
    assert not git.dests[0].exists()  # still cleaned up
    assert [e["reason"] for e in events(lines) if e["event"] == "run_failed"] == ["checkout_failed"]


def test_a_failed_clone_is_a_logged_failure_and_leaks_no_url_or_token(tmp_path):
    runner, lines, git, *_ = rig(tmp_path, lambda s: None, git=FakeCheckoutGit(fail=True))
    assert runner.run("fp1", "42") == "error"
    assert "SEKRET" not in "\n".join(lines)


def test_fresh_checkout_helper_removes_the_directory_on_exception(tmp_path):
    git = FakeCheckoutGit()
    with pytest.raises(ValueError):
        with fresh_checkout(git, parent=tmp_path) as path:
            assert path.exists()
            raise ValueError("inside")
    assert not git.dests[0].exists()
    assert list(tmp_path.iterdir()) == []


def test_fresh_checkout_helper_raises_checkout_error_when_unclean(tmp_path):
    with pytest.raises(CheckoutError):
        with fresh_checkout(FakeCheckoutGit(clean=False), parent=tmp_path):
            pass
    assert list(tmp_path.iterdir()) == []


# -- bounded run, no partial branch -----------------------------------------

def test_an_agent_error_is_a_logged_failure_and_deletes_the_partial_branch(tmp_path):
    branches = FakeBranchClient()  # absent before the run (#244 S1): this run creates it

    def behaviour(s):
        branches.push(BRANCH)
        raise RuntimeError("agent crashed after pushing")

    runner, lines, _, branches, _ = rig(tmp_path, behaviour, branches=branches)
    assert runner.run("fp1", "42") == "error"
    assert branches.deleted == [BRANCH] and BRANCH not in branches.branches
    ev = events(lines)
    assert any(e["event"] == "run_failed" and e["outcome"] == "error" for e in ev)
    assert any(e["event"] == "branch_deleted" and e["branch"] == BRANCH for e in ev)


def test_an_agent_reported_error_deletes_the_partial_branch(tmp_path):
    branches = FakeBranchClient()

    def behaviour(s):
        branches.push(BRANCH)
        return AgentResult("error", MODEL)

    runner, lines, _, branches, _ = rig(tmp_path, behaviour, branches=branches)
    assert runner.run("fp1", "42") == "error"
    assert branches.deleted == [BRANCH]


def test_pull_request_outcome_without_a_url_is_an_error_not_a_success(tmp_path):
    runner, *_ = rig(tmp_path, lambda s: AgentResult("pull_request_opened", MODEL))
    assert runner.run("fp1", "42") == "error"


def test_a_time_limit_ends_the_run_as_a_failure_and_deletes_the_branch(tmp_path):
    release = threading.Event()
    branches = FakeBranchClient()

    def behaviour(s):
        branches.push(BRANCH)  # pushed before the limit hit
        release.wait(10)
        return AgentResult("pull_request_opened", MODEL, pull_request="https://pr/1")

    try:
        runner, lines, git, branches, _ = rig(tmp_path, behaviour, timeout=0.2, branches=branches)
        assert runner.run("fp1", "42") == "error"
    finally:
        release.set()
    assert [e["reason"] for e in events(lines) if e["event"] == "run_failed"] == ["agent_timeout"]
    assert branches.deleted == [BRANCH]
    assert not git.dests[0].exists()


def test_false_positive_with_a_pushed_branch_leaves_no_branch(tmp_path):
    branches = FakeBranchClient()

    def behaviour(s):
        branches.push(BRANCH)
        return AgentResult("no_change", MODEL, explanation="fine")

    runner, lines, _, branches, _ = rig(tmp_path, behaviour, branches=branches)
    assert runner.run("fp1", "42") == "no_change"
    assert branches.deleted == [BRANCH]


def test_a_successful_pull_request_keeps_its_branch(tmp_path):
    runner, lines, _, branches, _ = rig(
        tmp_path, lambda s: AgentResult("pull_request_opened", MODEL, pull_request="https://pr/1"),
        branches=FakeBranchClient({BRANCH}))
    assert runner.run("fp1", "42") == "pull_request_opened"
    assert branches.deleted == [] and BRANCH in branches.branches


def test_no_agent_or_checkout_for_an_obvious_false_positive(tmp_path):
    runner, lines, git, branches, sessions = rig(tmp_path, lambda s: None)
    backend = FakeBackend()
    backend.add_finding("43", ["sent"])
    runner._api = ResponderApi("http://backend.test", "tok", transport=httpx.MockTransport(backend.handler))
    assert runner.run("fp1", "43") == "no_change"
    assert git.dests == [] and sessions == []


def test_a_failing_branch_cleanup_is_logged_but_the_run_still_ends_as_error(tmp_path):
    class Broken:
        def __init__(self):
            self.reads = 0

        def get_branch_sha(self, branch):
            self.reads += 1
            return None if self.reads == 1 else "created-by-this-run"  # absent before, present after

        def delete_branch_if_exists(self, branch):
            raise RuntimeError("network down")

    def behaviour(s):
        raise RuntimeError("boom")

    runner, lines, *_ = rig(tmp_path, behaviour, branches=Broken())
    assert runner.run("fp1", "42") == "error"
    assert any(e["event"] == "branch_cleanup_failed" for e in events(lines))


# -- the real REST branch client, against a mock transport -------------------

def test_rest_branch_client_deletes_an_existing_branch_and_ignores_a_missing_one():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, request.headers.get("authorization")))
        if request.method == "GET":
            return httpx.Response(200 if request.url.path.endswith("responder/fp1") else 404, json={})
        return httpx.Response(204)

    client = GitHubRestBranches("o/r", "TOKEN", transport=httpx.MockTransport(handler))
    assert client.delete_branch_if_exists("responder/fp1") is True
    assert client.delete_branch_if_exists("responder/none") is False
    assert ("DELETE", "/repos/o/r/git/refs/heads/responder/fp1", "Bearer TOKEN") in calls
    assert not any(m == "DELETE" and p.endswith("none") for m, p, _ in calls)


# -- the real git seam never puts the token in a URL or argument ------------

def test_git_auth_env_carries_the_token_only_in_the_environment():
    env = git_auth_env("TOKEN123")
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert "TOKEN123" not in "".join(v for k, v in env.items() if k != "GIT_CONFIG_VALUE_0")
    assert SubprocessGit("o/r", "TOKEN123")._url == "https://github.com/o/r.git"
