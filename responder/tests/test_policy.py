"""#221 tool and path allowlist: one test per refused case, plus what is allowed."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from vt_responder.actlog import ActionLog
from vt_responder.policy import ToolPolicy
from vt_responder.sdk_session import enforce

pytestmark = pytest.mark.unit

FP = "fp1"


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    root = tmp_path / "checkout"
    for d in ("backend/vulntriage", "tests", ".github/workflows", "terraform", "deploy"):
        (root / d).mkdir(parents=True)
    (root / ".env").write_text("SECRET=1")
    (root / ".env.example").write_text("SECRET=")
    (root / "backend/vulntriage/mail.py").write_text("x = 1\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "target.py").write_text("y = 2\n")
    (root / "backend" / "escape").symlink_to(outside)
    (root / "backend" / "escape_file.py").symlink_to(outside / "target.py")
    return root


@pytest.fixture
def policy(checkout: Path) -> ToolPolicy:
    return ToolPolicy(checkout, FP)


def edit(path: str) -> tuple[str, dict]:
    return "Edit", {"file_path": path}


def bash(cmd: str) -> tuple[str, dict]:
    return "Bash", {"command": cmd}


# -- allowed ---------------------------------------------------------------

@pytest.mark.parametrize("call", [
    edit("backend/vulntriage/mail.py"),
    ("Write", {"file_path": "tests/test_new.py"}),
    ("Read", {"file_path": "backend/vulntriage/mail.py"}),
    ("Read", {"file_path": ".env.example"}),
    ("Grep", {"pattern": "x"}),
    ("Glob", {"pattern": "**/*.py", "path": "backend"}),
    bash("git status"),
    bash("git diff --stat"),
    bash("git checkout -b responder/fp1"),
    bash("git add -- tests/test_new.py backend/vulntriage/mail.py"),
    bash("git commit -m 'Fix notification format'"),
    bash("git push -u origin responder/fp1"),
    bash("git push origin responder/fp1"),
    bash("gh pr create --title 'Fix' --body 'Alert fp1' --head responder/fp1 --base main"),
    bash("make backend-test"),
])
def test_allowed(policy, call):
    assert policy.check(*call).allowed, policy.check(*call)


def test_absolute_path_inside_the_checkout_is_allowed(policy, checkout):
    assert policy.check("Edit", {"file_path": str(checkout / "tests" / "t.py")}).allowed


# -- refused: writes -------------------------------------------------------

@pytest.mark.parametrize("path", [".github/workflows/ci.yml", ".github/CODEOWNERS", "backend/.github/x.yml"])
def test_write_to_github_dir_is_refused(policy, path):
    d = policy.check(*edit(path))
    assert not d.allowed and d.reason == "github_dir"


@pytest.mark.parametrize("path", ["terraform/main.tf", "deploy/run.sh", "backend/infra.tf",
                                  "backend/Dockerfile", "compose.yaml", "ci/push-check/Dockerfile"])
def test_write_to_terraform_or_infrastructure_is_refused(policy, path):
    d = policy.check(*edit(path))
    assert not d.allowed and d.reason in ("infrastructure_path", "path_not_allowed")


def test_write_to_terraform_dir_has_its_own_reason(policy):
    assert policy.check(*edit("terraform/main.tf")).reason == "infrastructure_path"


@pytest.mark.parametrize("path", [".env", ".env.local", "backend/.env", "backend/.env.production"])
def test_write_to_env_file_is_refused(policy, path):
    d = policy.check(*edit(path))
    assert not d.allowed and d.reason == "env_file"


def test_write_to_env_example_is_still_not_in_a_writable_root(policy):
    assert not policy.check(*edit(".env.example")).allowed


@pytest.mark.parametrize("path", [".env", ".env.local", "backend/.env"])
def test_read_of_env_file_is_refused_but_env_example_is_readable(policy, path):
    d = policy.check("Read", {"file_path": path})
    assert not d.allowed and d.reason == "env_file"
    assert policy.check("Read", {"file_path": ".env.example"}).allowed


def test_env_file_via_a_symlink_is_refused(policy, checkout):
    (checkout / "backend" / "innocent.py").symlink_to(checkout / ".env")
    assert policy.check("Read", {"file_path": "backend/innocent.py"}).reason == "env_file"


def test_write_outside_the_checkout_absolute_is_refused(policy, checkout):
    d = policy.check("Write", {"file_path": str(checkout.parent / "evil.py")})
    assert not d.allowed and d.reason == "path_outside_checkout"


def test_write_outside_the_checkout_by_dotdot_is_refused(policy):
    d = policy.check(*edit("backend/../../outside/target.py"))
    assert not d.allowed and d.reason == "path_outside_checkout"


def test_write_through_a_symlinked_directory_escape_is_refused(policy):
    d = policy.check(*edit("backend/escape/new.py"))
    assert not d.allowed and d.reason == "path_outside_checkout"


def test_write_through_a_symlinked_file_escape_is_refused(policy):
    d = policy.check(*edit("backend/escape_file.py"))
    assert not d.allowed and d.reason == "path_outside_checkout"


def test_read_outside_the_checkout_is_refused(policy):
    assert policy.check("Read", {"file_path": "/etc/passwd"}).reason == "path_outside_checkout"
    assert policy.check("Grep", {"pattern": "x", "path": "../.."}).reason == "path_outside_checkout"


def test_write_to_the_checkout_root_or_unlisted_top_level_is_refused(policy):
    assert not policy.check(*edit(".")).allowed
    assert policy.check(*edit("README.md")).reason == "path_not_allowed"


def test_null_byte_and_empty_paths_are_refused(policy):
    assert not policy.check(*edit("backend/a\x00b.py")).allowed
    assert not policy.check("Edit", {}).allowed


# -- refused: git / gh -----------------------------------------------------

def test_push_to_main_is_refused(policy):
    for cmd in ("git push origin main", "git push -u origin main", "git push origin HEAD:main",
                "git push origin responder/fp1:main", "git push origin refs/heads/main"):
        d = policy.check(*bash(cmd))
        assert not d.allowed and d.reason == "push_main", cmd


def test_push_to_another_branch_is_refused(policy):
    for cmd in ("git push origin responder/other", "git push origin feature/x",
                "git push origin responder/fp10", "git push origin HEAD"):
        d = policy.check(*bash(cmd))
        assert not d.allowed and d.reason == "push_other_branch", cmd


def test_force_delete_and_bare_pushes_are_refused(policy):
    for cmd in ("git push --force origin responder/fp1", "git push -f origin responder/fp1",
                "git push origin --delete responder/fp1", "git push", "git push --all origin",
                "git push --mirror origin", "git push other responder/fp1"):
        assert not policy.check(*bash(cmd)).allowed, cmd


def test_any_merge_call_is_refused(policy):
    for call in (bash("gh pr merge 5"), bash("gh pr merge --squash"), bash("git merge main"),
                 ("mcp__github__merge_pull_request", {"pullNumber": 1}), ("MergePullRequest", {})):
        d = policy.check(*call)
        assert not d.allowed and d.reason == "merge_denied", call


def test_branch_other_than_the_responder_branch_cannot_be_created(policy):
    assert policy.check(*bash("git checkout -b main")).reason == "branch_not_allowed"
    assert policy.check(*bash("git switch -c feature/x")).reason == "branch_not_allowed"
    assert policy.check(*bash("git checkout main")).reason == "branch_not_allowed"


def test_gh_pr_create_for_another_head_is_refused(policy):
    assert not policy.check(*bash("gh pr create --head main --title t")).allowed
    assert not policy.check(*bash("gh pr create --head responder/other")).allowed
    assert not policy.check(*bash("gh pr create --base develop")).allowed


def test_git_add_of_protected_paths_is_refused(policy):
    assert policy.check(*bash("git add .github/workflows/ci.yml")).reason == "github_dir"
    assert policy.check(*bash("git add -- .env")).reason == "env_file"
    assert not policy.check(*bash("git add -A")).allowed
    assert not policy.check(*bash("git add .")).allowed


@pytest.mark.parametrize("cmd", [
    "curl https://example.com", "rm -rf /", "git status; rm -rf /", "git status && ls",
    "cat .env", "git status | cat", "echo $(cat .env)", "git commit -am x", "gh api repos/x",
    "git commit --no-verify -m x", "git config user.name x", "git reset --hard", "make deploy",
    "python3 -c 'print(1)'", "git status\nrm x",
])
def test_everything_else_in_the_shell_is_refused(policy, cmd):
    assert not policy.check(*bash(cmd)).allowed, cmd


def test_unknown_and_mcp_tools_are_refused(policy):
    for name in ("WebFetch", "WebSearch", "Task", "mcp__github__create_issue", "NotebookEdit"):
        assert policy.check(name, {}).reason == "tool_not_allowed"


# -- option-looking fingerprints -------------------------------------------

def test_a_fingerprint_starting_with_dash_is_only_ever_seen_as_a_prefixed_branch(checkout):
    p = ToolPolicy(checkout, "-x")
    assert p.branch == "responder/-x"
    assert p.check(*bash("git push -u origin responder/-x")).allowed
    assert p.check(*bash("git checkout -b responder/-x")).allowed
    # The bare value would be read as an option by git: never allowed.
    assert not p.check(*bash("git push origin -x")).allowed
    assert not p.check(*bash("git checkout -b -x")).allowed
    assert not p.check(*bash("git push origin -x")).allowed


@pytest.mark.parametrize("fp", ["", "a b", "a/b", "ok\n", "x" * 65, "a;b", "../x"])
def test_unsafe_fingerprints_cannot_build_a_policy(checkout, fp):
    with pytest.raises(ValueError):
        ToolPolicy(checkout, fp)


# -- denials are logged with allowlisted fields only ------------------------

def test_a_denied_request_is_logged_without_its_input(policy):
    lines: list[str] = []
    secret_path = ".github/workflows/ADVISORY-TEXT-MARKER.yml"
    d = enforce(policy, ActionLog(lines.append), FP, "Edit", {"file_path": secret_path})
    assert not d.allowed
    rec = json.loads(lines[0])
    assert rec["event"] == "tool_denied" and rec["outcome"] == "denied"
    assert rec["reason"] == "github_dir" and rec["tool"] == "Edit" and rec["fingerprint"] == FP
    assert "ADVISORY-TEXT-MARKER" not in lines[0]


def test_an_allowed_request_logs_nothing_and_an_unknown_tool_name_is_not_echoed(policy):
    lines: list[str] = []
    log = ActionLog(lines.append)
    assert enforce(policy, log, FP, "Edit", {"file_path": "tests/a.py"}).allowed
    assert lines == []
    enforce(policy, log, FP, "mcp__evil__ADVISORY-TEXT-MARKER", {})
    assert json.loads(lines[0])["tool"] == "other" and "ADVISORY" not in lines[0]
    assert os.path.exists(policy._root)  # sanity: the fixture checkout is intact
