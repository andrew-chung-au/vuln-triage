"""#260: the `claude -p` allow/deny rules are generated from policy.py, and every refused case is
refused by the generated list.

`cli_rules.evaluate` is this repository's model of the documented rule semantics (deny first, `Bash(x *)`
prefix rules, `Edit(dir/**)` anchored at the working directory; code.claude.com/docs/en/permissions, read
2026-10-27). The real CLI is the authority; whether the model matches it is a VERIFY item for the first
live run (_docs/responder-cli-runtime.md). The same cases are checked against `ToolPolicy`, so the
generated rules and the policy cannot drift apart unnoticed.
"""

from __future__ import annotations

import pytest

from vt_responder import policy
from vt_responder.cli_rules import DENIED_TOOLS, build_rules, evaluate

pytestmark = pytest.mark.unit

RULES = build_rules()


def check(tmp_path, tool, arg):
    return evaluate(RULES, tmp_path, tool, arg)


# -- generated from the policy: one source ---------------------------------------------------

def test_the_rules_are_built_from_the_policy_constants():
    for root in policy.WRITABLE_ROOTS:
        assert f"Edit({root}/**)" in RULES.allowed
    for target in policy.MAKE_TARGETS:
        assert f"Bash(make {target})" in RULES.allowed
    for sub in (*policy.CLI_GIT_READ, *policy.CLI_GIT_WRITE):
        assert f"Bash(git {sub} *)" in RULES.allowed
    for component in policy.PROTECTED_COMPONENTS:
        assert f"Edit(**/{component}/**)" in RULES.denied
    for suffix in policy.PROTECTED_SUFFIXES:
        assert f"Edit(**/*{suffix})" in RULES.denied
    for name in policy.PROTECTED_LOCKFILES:
        assert f"Edit(**/{name})" in RULES.denied
    for prefix in policy.PROTECTED_PATH_PREFIXES:
        assert f"Edit({prefix}**)" in RULES.denied
    assert set(RULES.tools) == set(policy.KNOWN_TOOLS)


def test_the_agent_gets_no_web_tool_no_bare_read_and_no_push():
    for tool in DENIED_TOOLS:
        assert tool in RULES.denied and tool not in RULES.tools
    assert "Read" not in RULES.allowed and "Bash" not in RULES.allowed  # a bare allow would reach outside the checkout
    assert not any("push" in rule for rule in RULES.allowed)
    assert not any(rule.startswith(("Bash(gh", "Bash(curl", "Bash(uv", "Bash(npm")) for rule in RULES.allowed)


def test_argv_passes_each_list_as_one_comma_joined_value():
    argv = RULES.argv()
    assert argv[0::2] == ["--tools", "--allowedTools", "--disallowedTools"]
    assert argv[1] == ",".join(RULES.tools) and argv[3] == ",".join(RULES.allowed)
    assert not any("," in rule for rule in (*RULES.tools, *RULES.allowed, *RULES.denied))


# -- allowed -----------------------------------------------------------------------------------

ALLOWED = [
    ("Bash", "make backend-test"), ("Bash", "make responder-test"), ("Bash", "make test"),
    ("Bash", "git status"), ("Bash", "git status --short"), ("Bash", "git diff --stat"),
    ("Bash", "git log --oneline"), ("Bash", "git add backend/app/service.py tests/test_x.py"),
    ("Bash", "git commit -m 'fix the retry'"),
    ("Edit", "backend/app/service.py"), ("Write", "tests/test_retry.py"), ("MultiEdit", "frontend/src/a.ts"),
    ("Edit", "responder/tests/test_x.py"),
    ("Read", "backend/app/service.py"), ("Read", ".env.example"), ("Grep", "backend"), ("Glob", "tests"),
]


@pytest.mark.parametrize("tool,arg", ALLOWED)
def test_the_expected_work_is_allowed_by_the_rules_and_by_the_policy(tmp_path, tool, arg):
    assert check(tmp_path, tool, arg).allowed
    pol = policy.ToolPolicy(tmp_path, "fp1")
    if tool == "Bash":
        assert pol.check("Bash", {"command": arg}).allowed
    elif tool in ("Grep", "Glob"):
        assert pol.check(tool, {"path": arg}).allowed
    elif tool == "Read":
        assert pol.check(tool, {"file_path": arg}).allowed
    else:
        assert pol.check(tool, {"file_path": arg}).allowed


# -- refused: one test per case, against the generated rules AND the policy ---------------------

# The SDK runtime's policy lets the AGENT push its own branch and open a pull request; the CLI runtime's
# agent has neither (the runner does both), so these are refused by the rules but not by ToolPolicy.
REFUSED_CLI_ONLY = ["git push origin responder/fp1", "git push -u origin responder/fp1",
                    "gh pr create --title x --head responder/fp1"]

REFUSED_BASH = [
    "git push", "git push -u origin main", "git push --force origin main",
    "gh api repos/o/r", "curl https://example.com", "wget https://example.com",
    "make install", "make backend-install", "make responder-install", "uv sync", "uv run pytest", "npm ci",
    "npm install", "pytest", "pytest backend/tests", "python3 -m pytest", "git merge main", "git checkout -b other",
    "git config user.name x", "git remote add evil https://evil.example/r.git", "git reset --hard", "make dev",
    "make backend-test extra", "rm -rf /", "cat /etc/passwd", "git status && curl https://example.com",
    "git status; git push", "git status | sh", "git status $(curl https://example.com)",
    "git status `curl https://example.com`", "git add backend/x > ../out",
    # not matched by a deny rule (other spelling) but not allowed either: dontAsk refuses it
    "git -C . push origin main", "git -c push.default=current push", "/usr/bin/curl https://example.com",
    "sh -c 'curl https://example.com'", "env curl https://example.com",
]


@pytest.mark.parametrize("command", REFUSED_BASH)
def test_a_refused_command_is_refused_by_the_generated_rules_and_by_the_policy(tmp_path, command):
    assert not check(tmp_path, "Bash", command).allowed
    assert not policy.ToolPolicy(tmp_path, "fp1").check("Bash", {"command": command}).allowed


@pytest.mark.parametrize("command", REFUSED_CLI_ONLY)
def test_the_cli_agent_may_not_push_its_branch_or_open_a_pull_request(tmp_path, command):
    assert not check(tmp_path, "Bash", command).allowed


@pytest.mark.parametrize("tool", ["WebFetch", "WebSearch", "Task", "NotebookEdit", "mcp__github__push_files"])
def test_a_tool_outside_the_set_is_refused(tmp_path, tool):
    assert not check(tmp_path, tool, "https://example.com").allowed
    assert not policy.ToolPolicy(tmp_path, "fp1").check(tool, {"url": "https://example.com"}).allowed


REFUSED_EDIT = [
    ".github/workflows/verify.yml", "backend/.github/workflows/x.yml", "terraform/main.tf", "backend/infra/x.py",
    "backend/deploy/x.py", "backend/ci/x.py", "backend/observability/x.yml", "backend/.devcontainer/x.json",
    "backend/.git/config", "backend/.claude/settings.json", "backend/net.tf", "backend/prod.tfvars",
    "backend/.env", "frontend/.env.local", "backend/.env.example", "Dockerfile", "backend/Dockerfile",
    "compose.yaml", "backend/compose.override.yml", "frontend/package-lock.json", "backend/uv.lock",
    "responder/uv.lock", "responder/vt_responder/policy.py", "responder/vt_responder/envscrub.py",
    "responder/vt_responder/cli_session.py", "docs/notes.md", "README.md", "_docs/specs.md", "Makefile",
    "../outside.py", "/etc/passwd", "/root/.claude/.credentials.json",
]


@pytest.mark.parametrize("path", REFUSED_EDIT)
def test_a_refused_edit_is_refused_by_the_generated_rules_and_the_publish_gate(tmp_path, path):
    for tool in ("Edit", "Write"):
        assert not check(tmp_path, tool, path).allowed, tool
    assert not policy.ToolPolicy(tmp_path, "fp1").check_publish_path(path).allowed


REFUSED_READ = ["backend/.env", ".env", "frontend/.env.local", "../secret.txt", "/etc/passwd",
                "/root/.claude/.credentials.json"]


@pytest.mark.parametrize("path", REFUSED_READ)
def test_a_refused_read_is_refused_by_the_generated_rules_and_by_the_policy(tmp_path, path):
    for tool in ("Read", "Grep", "Glob"):
        assert not check(tmp_path, tool, path).allowed, tool
    assert not policy.ToolPolicy(tmp_path, "fp1").check_read_path(path).allowed


def test_deny_wins_over_a_matching_allow_rule(tmp_path):
    # backend/** is allowed for Edit, and the .github component under it is denied: the deny decides.
    assert any(r == "Edit(backend/**)" for r in RULES.allowed)
    assert not check(tmp_path, "Edit", "backend/.github/x.yml").allowed
    assert check(tmp_path, "Edit", "backend/app/x.py").allowed


def test_what_a_cli_rule_cannot_express_is_left_to_the_diff_gate(tmp_path):
    """`git add *` cannot constrain the path (the docs call argument rules fragile), so the rules
    allow `git add .github/x.yml`; the policy refuses it and the runner's diff gate refuses the push
    (test_publisher.py). Stated here so the gap is visible, not hidden."""
    assert check(tmp_path, "Bash", "git add .github/workflows/x.yml").allowed
    assert not policy.ToolPolicy(tmp_path, "fp1").check("Bash", {"command": "git add .github/workflows/x.yml"}).allowed
