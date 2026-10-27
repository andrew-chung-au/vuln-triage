"""#260: the runner-side diff gate, push and pull request, driven by a FAKE git and a FAKE GitHub client.

Independent of what the CLI enforced: every refused case here must stop the push, whatever the agent
did. No git, no network, no token.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vt_responder.fakes import FakeBranchClient
from vt_responder.publisher import (
    Change,
    GitPublisher,
    PublishError,
    SubprocessPublishGit,
    check_changes,
    compose_pull_request,
)

pytestmark = pytest.mark.unit

BASE, NEW = "a" * 40, "b" * 40
BRANCH = "responder/fp1"
GOOD = [Change("M", "100644", "100644", "backend/app/service.py"), Change("A", "000000", "100644", "tests/test_x.py")]


class FakePublishGit:
    """Scripted answers to the git questions the gate asks; records pushes. Never runs git."""

    def __init__(self, changes=None, *, commits=1, merges=0, ancestor=True, digests=("d1", "d1"),
                 fail=None, fail_push=False, branches: FakeBranchClient | None = None, new_head=NEW):
        self.changes_list = list(GOOD if changes is None else changes)
        self.commits, self.merges, self.ancestor = commits, merges, ancestor
        self.digests, self.fail, self.fail_push, self.branches, self.new_head = digests, fail, fail_push, branches, new_head
        self.head_calls = self.digest_calls = 0
        self.pushed: list[tuple[str, str]] = []

    def _maybe_fail(self, name):
        if self.fail == name:
            raise RuntimeError("git failed")

    def head(self, checkout):
        self.head_calls += 1
        return BASE if self.head_calls == 1 else self.new_head  # first call: the clone; later: after the agent

    def config_digest(self, checkout):
        self.digest_calls += 1
        return self.digests[min(self.digest_calls - 1, len(self.digests) - 1)]

    def is_ancestor(self, checkout, base, head):
        self._maybe_fail("is_ancestor")
        return self.ancestor

    def commit_count(self, checkout, base, head):
        return self.commits

    def merge_count(self, checkout, base, head):
        return self.merges

    def changes(self, checkout, base, head):
        self._maybe_fail("changes")
        return self.changes_list

    def push(self, checkout, sha, branch):
        if self.fail_push:
            raise RuntimeError("push to https://x-access-token:SEKRET@github.com failed")
        self.pushed.append((sha, branch))
        if self.branches is not None:
            self.branches.push(branch)


def gate(tmp_path: Path, git: FakePublishGit, *, branches=None, summary="fixed the retry", max_commits=3,
         secrets=()):
    branches = branches if branches is not None else FakeBranchClient()
    publisher = GitPublisher(git, branches, secrets=secrets, max_commits=max_commits)
    snapshot = publisher.snapshot(tmp_path)
    return publisher, snapshot, branches


def publish(tmp_path, git, **kw):
    publisher, snapshot, branches = gate(tmp_path, git, **{k: v for k, v in kw.items() if k != "summary"})
    url = publisher.publish(tmp_path, snapshot, "fp1", "42", kw.get("summary", "fixed the retry"))
    return url, branches


def refused(tmp_path, git, reason, **kw):
    with pytest.raises(PublishError) as err:
        publish(tmp_path, git, **kw)
    assert err.value.reason == reason
    assert git.pushed == []  # nothing left the machine


# -- a good diff is pushed and a pull request is opened by the runner --------------------------

def test_a_good_diff_is_pushed_to_the_responder_branch_and_a_pull_request_is_opened(tmp_path):
    git = FakePublishGit()
    url, branches = publish(tmp_path, git)
    assert git.pushed == [(NEW, BRANCH)]  # the checked head sha, to responder/<fp>, nothing else
    assert branches.created and branches.created[0]["head"] == BRANCH and branches.created[0]["base"] == "main"
    assert url == "https://github.com/owner/repo/pull/100"
    title, body = branches.created[0]["title"], branches.created[0]["body"]
    assert "fp1" in title and "backend/app/service.py" in body and "tests/test_x.py" in body


# -- every refused case ----------------------------------------------------------------------

@pytest.mark.parametrize("path,why", [
    ("docs/notes.md", "diff_path_path_not_allowed"),
    ("README.md", "diff_path_path_not_allowed"),
    (".github/workflows/verify.yml", "diff_path_github_dir"),
    ("backend/.github/workflows/x.yml", "diff_path_github_dir"),
    ("backend/.GitHub/x.yml", "diff_path_github_dir"),
    ("terraform/main.tf", "diff_path_infrastructure_path"),
    ("backend/infra/x.py", "diff_path_infrastructure_path"),
    ("backend/deploy/x.py", "diff_path_infrastructure_path"),
    ("backend/net.tfvars", "diff_path_infrastructure_path"),
    ("backend/Dockerfile", "diff_path_infrastructure_path"),
    ("frontend/compose.override.yml", "diff_path_infrastructure_path"),
    ("backend/.env", "diff_path_env_file"),
    ("frontend/.env.local", "diff_path_env_file"),
    ("backend/.env.example", "diff_path_env_file"),
    ("frontend/package-lock.json", "diff_path_lockfile"),
    ("backend/uv.lock", "diff_path_lockfile"),
    ("responder/uv.lock", "diff_path_lockfile"),
    ("responder/vt_responder/policy.py", "diff_path_guard_module"),
    ("responder/vt_responder/envscrub.py", "diff_path_guard_module"),
    ("responder/vt_responder/cli_session.py", "diff_path_guard_module"),
    ("responder/vt_responder/publisher.py", "diff_path_guard_module"),
    ("Responder/VT_Responder/policy.py", "diff_path_path_not_allowed"),  # not a writable root at all
    ("../escape.py", "diff_path_path_outside_checkout"),
    ("backend/.git/hooks/pre-push", "diff_path_infrastructure_path"),
    (".claude/settings.json", "diff_path_infrastructure_path"),
    ("backend/.devcontainer/x.json", "diff_path_infrastructure_path"),
])
def test_a_changed_file_outside_the_writable_roots_or_on_a_protected_path_refuses_the_push(tmp_path, path, why):
    refused(tmp_path, FakePublishGit([Change("A", "000000", "100644", path)]), why)


def test_a_protected_file_among_good_ones_still_refuses_the_whole_push(tmp_path):
    changes = [*GOOD, Change("M", "100644", "100644", ".github/workflows/verify.yml")]
    refused(tmp_path, FakePublishGit(changes), "diff_path_github_dir")


def test_a_deleted_protected_file_is_refused_too(tmp_path):
    refused(tmp_path, FakePublishGit([Change("D", "100644", "000000", ".github/CODEOWNERS")]), "diff_path_github_dir")


@pytest.mark.parametrize("change,why", [
    (Change("A", "000000", "120000", "backend/link"), "diff_symlink"),
    (Change("M", "100644", "120000", "backend/app/x.py"), "diff_symlink"),
    (Change("T", "100644", "120000", "backend/app/x.py"), "diff_type_change"),
    (Change("T", "100644", "100755", "backend/app/x.py"), "diff_type_change"),
    (Change("A", "000000", "160000", "backend/vendor"), "diff_submodule"),
    (Change("A", "000000", "100755", "backend/run.sh"), "diff_mode_unexpected"),  # a new executable
    (Change("M", "100644", "100755", "backend/app/x.py"), "diff_mode_changed"),  # chmod +x
    (Change("M", "100755", "100644", "backend/app/x.sh"), "diff_mode_changed"),
    (Change("R", "100644", "100644", "backend/app/x.py"), "diff_status_unexpected"),
    (Change("A", "000000", "100644", "backend/a\nb.py"), "diff_path_odd_name"),
])
def test_a_symlink_submodule_type_change_or_unexpected_mode_refuses_the_push(tmp_path, change, why):
    refused(tmp_path, FakePublishGit([change]), why)


def test_deleting_a_symlink_is_refused(tmp_path):
    refused(tmp_path, FakePublishGit([Change("D", "120000", "000000", "backend/link")]), "diff_symlink")


def test_more_commits_than_the_maximum_refuses_the_push(tmp_path):
    refused(tmp_path, FakePublishGit(commits=4), "too_many_commits")
    url, _ = publish(tmp_path, FakePublishGit(commits=3))  # exactly the maximum is fine
    assert url
    refused(tmp_path, FakePublishGit(commits=2), "too_many_commits", max_commits=1)


def test_a_merge_commit_refuses_the_push(tmp_path):
    refused(tmp_path, FakePublishGit(merges=1), "merge_commit")


def test_a_head_that_does_not_descend_from_the_cloned_head_refuses_the_push(tmp_path):
    refused(tmp_path, FakePublishGit(ancestor=False), "base_not_cloned_head")


def test_no_new_commit_refuses_the_push(tmp_path):
    refused(tmp_path, FakePublishGit(new_head=BASE), "no_commits")


def test_a_commit_that_changes_no_file_refuses_the_push(tmp_path):
    refused(tmp_path, FakePublishGit([]), "diff_empty")


def test_too_many_files_refuses_the_push(tmp_path):
    many = [Change("A", "000000", "100644", f"tests/t{i}.py") for i in range(41)]
    refused(tmp_path, FakePublishGit(many), "diff_too_many_files")


def test_a_modified_git_config_refuses_the_push(tmp_path):
    refused(tmp_path, FakePublishGit(digests=("d1", "d2")), "git_config_modified")


def test_a_git_failure_while_checking_is_a_refusal_not_a_push(tmp_path):
    refused(tmp_path, FakePublishGit(fail="changes"), "diff_check_failed")
    refused(tmp_path, FakePublishGit(fail="is_ancestor"), "diff_check_failed")


def test_a_failed_push_is_a_failed_run_and_leaks_nothing(tmp_path):
    git = FakePublishGit(fail_push=True)
    publisher, snapshot, _ = gate(tmp_path, git)
    with pytest.raises(PublishError) as err:
        publisher.publish(tmp_path, snapshot, "fp1", "42", "x")
    assert err.value.reason == "push_failed" and "SEKRET" not in repr(err.value)


def test_a_failed_pull_request_creation_is_a_failed_run(tmp_path):
    branches = FakeBranchClient()
    branches.fail_create = True
    publisher, snapshot, _ = gate(tmp_path, FakePublishGit(branches=branches), branches=branches)
    with pytest.raises(PublishError) as err:
        publisher.publish(tmp_path, snapshot, "fp1", "42", "x")
    assert err.value.reason == "pull_request_create_failed"


# -- the body: composed by the runner, agent text redacted, short, no advisory text ------------

def test_the_agent_summary_is_redacted_shortened_and_fenced(tmp_path):
    secret = "ghp_PLANTEDsecretvalue123"
    summary = f"retry fixed {secret} " + "word " * 200 + "@octocat `rm -rf` ```"
    _, branches = publish(tmp_path, FakePublishGit(), summary=summary, secrets=[secret])
    body = branches.created[0]["body"]
    assert secret not in body and "[REDACTED]" in body
    assert "`rm -rf`" not in body and "```\nretry" in body  # backticks neutralised, the text is in a fence
    fenced = body.split("```")[1]
    assert len(fenced.strip()) <= 300


def test_the_body_has_no_text_from_the_api_and_no_advisory_text(tmp_path):
    title, body = compose_pull_request("fp1", "42", ["backend/a.py"], None, [])
    assert "Agent summary" not in body  # nothing from the agent when it said nothing
    for text in (title, body):
        assert "ADVISORY" not in text and "ignore previous" not in text


def test_the_title_and_body_name_only_validated_identifiers():
    title, body = compose_pull_request("fp1", None, ["backend/a.py"], "s", [])
    assert title == "Fix undelivered notification for alert fp1"
    assert "finding" not in body.splitlines()[0]


def test_check_changes_accepts_a_good_diff(tmp_path):
    assert check_changes(tmp_path, "fp1", GOOD) == ["backend/app/service.py", "tests/test_x.py"]


# -- the real git seam parses `git diff --raw -z` and refuses odd pushes (no git is run) -------

def test_the_real_git_seam_parses_raw_diff_output(monkeypatch, tmp_path):
    import subprocess

    raw = (":100644 100644 aaa bbb M\0backend/app/service.py\0"
           ":000000 120000 000 ccc A\0backend/link\0"
           ":100644 000000 ddd 000 D\0tests/old.py\0")

    def fake_run(argv, **kwargs):
        assert "core.hooksPath=/dev/null" in argv and "core.fsmonitor=false" in argv
        return subprocess.CompletedProcess(argv, 0, stdout=raw, stderr="")

    monkeypatch.setattr("vt_responder.publisher.subprocess.run", fake_run)
    changes = SubprocessPublishGit("o/r", "TOK").changes(tmp_path, BASE, NEW)
    assert changes == [Change("M", "100644", "100644", "backend/app/service.py"),
                       Change("A", "000000", "120000", "backend/link"),
                       Change("D", "100644", "000000", "tests/old.py")]


def test_the_real_git_push_uses_an_explicit_url_a_sha_refspec_no_force_and_only_here_the_token(monkeypatch, tmp_path):
    import subprocess

    seen = []

    def fake_run(argv, **kwargs):
        seen.append((argv, kwargs["env"]))
        return subprocess.CompletedProcess(argv, 0, stdout=f"{NEW}\n", stderr="")

    monkeypatch.setattr("vt_responder.publisher.subprocess.run", fake_run)
    monkeypatch.setenv("RESPONDER_API_TOKEN", "PLANTED-RESPONDER-API-TOKEN")
    git = SubprocessPublishGit("o/r", "TOK123")
    git.head(tmp_path)
    git.push(tmp_path, NEW, BRANCH)
    (head_argv, head_env), (push_argv, push_env) = seen
    assert "GIT_CONFIG_VALUE_0" not in head_env  # read-only calls carry no credential
    assert "GIT_CONFIG_VALUE_0" in push_env and "RESPONDER_API_TOKEN" not in push_env
    assert push_argv[-3:] == ["--", "https://github.com/o/r.git", f"{NEW}:refs/heads/{BRANCH}"]
    assert not any(a in ("--force", "-f", "--delete", "--mirror", "--all") for a in push_argv)
    assert "TOK123" not in "".join(push_argv)
    for bad_sha, bad_branch in [("nothex", BRANCH), (NEW, "main"), (NEW, "refs/heads/main")]:
        with pytest.raises(RuntimeError):
            git.push(tmp_path, bad_sha, bad_branch)
