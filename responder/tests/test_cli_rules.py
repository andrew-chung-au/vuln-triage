"""#260: the `claude -p` allow/deny rules are generated from policy.py, and every refused case is
refused by the generated list.

`cli_rules.evaluate` is this repository's model of the documented rule semantics (deny first, `Bash(x *)`
prefix rules, `Edit(dir/**)` anchored at the working directory; code.claude.com/docs/en/permissions, read
2026-10-27). The real CLI is the authority; whether the model matches it is a VERIFY item for the first
live run (_docs/responder-cli-runtime.md). The same cases are checked against `ToolPolicy`, so the
generated rules and the policy cannot drift apart unnoticed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vt_responder import cli_rules, policy
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
    for sub in policy.CLI_GIT_READ:
        assert f"Bash(git {sub} *)" in RULES.allowed
    # git add / git commit are NOT allowed with a bare `*` any more (QA finding 2): per writable root, and `-m` only
    assert set(policy.CLI_GIT_WRITE) == {"add", "commit"}
    assert "Bash(git add *)" not in RULES.allowed and "Bash(git commit *)" not in RULES.allowed
    for root in policy.WRITABLE_ROOTS:
        assert f"Bash(git add {root}/*)" in RULES.allowed
    # `-m` with ONE quoted message (round 2): an unquoted or trailing word cannot be a pathspec argument
    assert "Bash(git commit -m '*')" in RULES.allowed and 'Bash(git commit -m "*")' in RULES.allowed
    assert "Bash(git commit -m *)" not in RULES.allowed
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
    ("Bash", "git log --oneline"), ("Bash", "git add backend/app/service.py"), ("Bash", "git add tests/test_x.py"),
    ("Bash", 'git commit -m "Don\'t drop failed jobs"'), ("Bash", 'git commit -m "Fix: handle None in notifier"'),
    ("Bash", "git commit -m 'fix #123: retry the job'"),
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
                    "gh pr create --title x --head responder/fp1",
                    # stricter than ToolPolicy (the diff gate is what refuses a lockfile; the `--` form is simply not offered)
                    "git add backend/uv.lock", "git add frontend/package-lock.json", "git add -- backend/x",
                    # broader than the policy's protected names (which start with "compose"), and quoted paths
                    "git add backend/docker-compose.yml", "git add 'backend/x.py'"]

REFUSED_BASH = [
    "git push", "git push -u origin main", "git push --force origin main",
    "gh api repos/o/r", "curl https://example.com", "wget https://example.com",
    "make install", "make backend-install", "make responder-install", "uv sync", "uv run pytest", "npm ci",
    "npm install", "pytest", "pytest backend/tests", "python3 -m pytest", "git merge main", "git checkout -b other",
    "git config user.name x", "git remote add evil https://evil.example/r.git", "git reset --hard", "make dev",
    "make backend-test extra", "rm -rf /", "cat /etc/passwd", "git status && curl https://example.com",
    # QA finding 2: more than ToolPolicy allows
    "git diff --output=/tmp/out", "git diff --output=out.txt backend", "git log --output=/tmp/out",
    "git log --oneline --output=/tmp/out", "git diff --no-index /etc/passwd /etc/hosts", "git diff --no-index backend",
    "git diff --ext-diff", "git diff --textconv",
    "git add -A", "git add .", "git add --force .github/x", "git add -f backend/x", "git add -u",
    "git add backend/x -A", "git add backend/x .github/workflows/x.yml", "git add backend/x ../outside",
    "git add --all", "git add /etc/passwd",
    "git commit --amend", "git commit -am 'x'", "git commit -m 'x' --amend", "git commit -m 'x' --no-verify",
    "git commit --no-verify -m 'x'", "git commit -m 'x' -a", "git commit", "git commit -F msg.txt",
    "git commit --allow-empty -m 'x'", "git commit -m 'x' --author=a",
    "git status; git push", "git status | sh", "git status $(curl https://example.com)",
    "git status `curl https://example.com`", "git add backend/x > ../out",
    # not matched by a deny rule (other spelling) but not allowed either: dontAsk refuses it
    "git -C . push origin main", "git -c push.default=current push", "/usr/bin/curl https://example.com",
    "sh -c 'curl https://example.com'", "env curl https://example.com",
]


# QA round 2, finding 2: forms the first patterns missed. Quote-split and backslash-split long options, every prefix
# abbreviation of a denied long option, commit flag abbreviations and extra arguments, protected names the patterns did
# not list, and glob/quote characters in `git add` paths.
DENIED_LONG_OPTIONS = ("--output", "--no-index", "--ext-diff", "--textconv", "--orderfile")
ABBREVIATIONS = [f"git {sub} {opt[:n]}{tail}" for sub in policy.CLI_GIT_READ for opt in DENIED_LONG_OPTIONS
                 for n in range(3, len(opt) + 1) for tail in ("=/tmp/x", " /tmp/x")]
REFUSED_BASH_ROUND2 = [
    'git diff --o"utput=/tmp/x"', "git diff --o\\utput=/tmp/x", 'git diff --"output=/tmp/x"', "git diff --'output'=/tmp/x",
    'git log --format=%B --o"utput=/tmp/x"', 'git status --o"utput=/tmp/x"', "git diff --ou\\tput /tmp/x",
    "git diff --OUTPUT=/tmp/x", "git diff -O/tmp/x", "git diff -O /tmp/x", "git diff --orderfile=/tmp/x",
    'git diff --no-"index" backend', 'git log --text"conv"',
    "git commit --am -m 'x'", "git commit -m 'x' --am", "git commit -m 'x' --amen", "git commit -m 'x' --no-ver",
    "git commit -m 'x' --al", "git commit -m 'x' --dry-run", "git commit -m 'x' --untracked-files",
    "git commit -m 'x' -- .github/workflows/x.yml", "git commit -m 'x' -- backend/x.py", "git commit -m 'x' y",
    "git commit -m x y", "git commit -m 'x' 'y'", 'git commit -m "x" y', "git commit -m 'x' backend/a.py",
    "git commit -m", "git commit -m 'x' -p", "git commit -m 'x' -",
    "git add backend/x -- .github/x", "git add tests/compose.yaml",
    "git add responder/compose.yaml",
    "git add backend/*", "git add responder/vt_resp*/x.py",
    'git add backend/.gi"thub"/x.yml', "git add backend/.gi\\thub/x.yml", "git add backend/.gi'thub'/x.yml",
]


# QA round 3, finding F1: shell expansion (`$`, `{`, `}`) rebuilds a denied flag or a protected path after the rules
# have looked at the raw text (`--${u}output=x` runs as `--output=x` when `u` is unset; `{a,b}` is brace expansion).
REFUSED_BASH_ROUND3 = [
    "git diff --${u}output=/x", "git diff --o${u}utput=/x", "git diff -${u}-output=/x",
    "git log -1 --format=%B --${u}output=/x", "git status --${u}output=/x", "git diff --${u}no-index /etc/passwd /etc/hosts",
    "git diff --${u}ext-diff", "git diff --${u}textconv", "git log --${u}orderfile=/x", "git diff -${u}O/x",
    "git diff --o{u,u}tput=/x", "git diff --o$u" + "tput=/x", "git diff $HOME", "git log {a,b}", "git status }",
    "git add backend/.en${u}v", "git add backend/x .git${u}hub/y", "git add backend/{.github,x}/y",
    "git add backend/x ${u}-A", "git add backend/x ${u}-f", "git add backend/$HOME", "git add backend/x{,}",
    "git commit -m 'x' ${u}--amend", 'git commit -m "x" ${u}-a', "git commit -m '$HOME'", 'git commit -m "${u}"',
    "git commit -m '{x}'",
]


# QA round 4, N1: bash splits words on a TAB as well as a space, so the space-based `git commit` denials
# (`* -*`, a quote then a space) did not see `git commit -m "x"<TAB>-a<TAB>-m "y"`; real git ran `-a`.
# These smuggle an argument or flag by tab: refused by the rules AND by ToolPolicy (which splits like the shell).
TAB_SMUGGLED = [
    'git commit -m "x"\t-a\t-m "y"', 'git commit -m "x"\t-a "y"', "git commit -m 'x'\t-a", 'git commit\t-a -m "x"',
    'git commit -m "x"\t--amend', 'git commit -m "x"\ty', 'git commit -m "x"\t-n', 'git commit -m "x"\t-s',
    'git commit -m "x"\t-F\tmsg.txt', 'git commit -m "x"\t-C\tHEAD',
    "git status\t--output=/x", "git diff\t--output=/x", "git diff --stat\t--no-index\ta\tb", "git log\t-1\t--output=/x",
    "git diff\t-O/x", "git log -1\t--ext-diff",
]
# Tab elsewhere, and the other ASCII whitespace controls. Bash does not split words on VT, FF or CR (only on space,
# tab and newline), so these are literal characters, harmless to git; the rules refuse them anyway for every allowed
# git command. ToolPolicy is not asserted: it treats a tab between words as the shell does (a legitimate commit).
CONTROL_WHITESPACE = [
    'git commit\t-m "x"', 'git commit -m\t"x"', "git add\tbackend/x", "git status\t--short",
    *[f'git commit -m "x"{c}-a{c}-m "y"' for c in ("\x0b", "\x0c", "\r")],
    *[f"git diff{c}--output=/x" for c in ("\x0b", "\x0c", "\r")],
]
# Control whitespace after a `git add` path, or inside a commit message. The deny patterns that used to refuse these are
# gone (the real CLI reads a control character in a pattern as a space, 2026-10-28 probe W1). A tab inside the quotes is
# part of the message word (harmless). For `git add` the rules (as modelled: the command text is matched raw) allow the
# form; whether the real CLI normalises a tab in the command before matching is unverified (VERIFY). ToolPolicy still
# refuses it, and the runner's diff gate (publisher.py) refuses any path outside the writable roots, protected paths
# and lockfiles whatever got staged: that gate is the only backstop for these forms. (VT and FF are not word separators in
# bash: `git add backend/x<VT>-A` names one odd file under backend/, so it is not listed here.)
DIFF_GATE_ONLY = [
    "git add backend/x\t-A", "git add backend/x\t.github/y", "git add backend/x\t-f", "git add backend/x\r-A", "git add backend/x\t.github/workflows/x.yml",
]


@pytest.mark.parametrize("command", DIFF_GATE_ONLY)
def test_control_whitespace_after_a_git_add_path_is_caught_only_by_the_policy_and_the_diff_gate(tmp_path, command):
    assert not policy.ToolPolicy(tmp_path, "fp1").check("Bash", {"command": command}).allowed


def test_a_tab_inside_the_commit_message_is_part_of_the_message(tmp_path):
    assert check(tmp_path, "Bash", 'git commit -m "x\ty"').allowed


def test_no_rule_pattern_contains_a_control_whitespace_character():
    """Measured 2026-10-28 with the real claude 2.1.311 (probe W1): a control-whitespace character inside a rule
    pattern is read as a space, so ``Bash(git commit *<TAB>*)`` denied every commit with a space in its message."""
    bad = [r for r in (*cli_rules.build_rules().allowed, *cli_rules.build_rules().denied)
           if any(c in r for c in "\t\x0b\x0c\r")]
    assert not bad, bad[:5]


@pytest.mark.parametrize("command", [
    'git commit -m "Handle findings with no fixed version in owner notification"',
    'git commit -m "Fix: don\'t fail for findings with no fix"', "git commit -m 'fix #123: retry the job'",
    "git diff --cached tests/x.py", "git diff --stat backend tests", "git log -1 --oneline backend/a.py",
    "git status --short backend", "git add backend/a.py", "git add tests/test_x.py"])
def test_ordinary_commits_and_two_argument_reads_are_not_over_denied(tmp_path, command):
    assert check(tmp_path, "Bash", command).allowed, command


def test_the_model_reads_a_control_character_in_a_pattern_as_a_space():
    """The model must reflect the CLI, so it would have caught the over-denial: this pattern is ``git commit * *``."""
    rules = cli_rules.CliToolRules(("Bash",), ('Bash(git commit -m "*")',), ("Bash(git commit *\t*)",))
    assert not cli_rules.evaluate(rules, Path("/x"), "Bash", 'git commit -m "a b"').allowed
    assert cli_rules._command_pattern("git commit *\t*").pattern == cli_rules._command_pattern("git commit * *").pattern
    assert cli_rules._command_pattern("git add *\x0b*").pattern == cli_rules._command_pattern("git add * *").pattern


@pytest.mark.parametrize("command", TAB_SMUGGLED)
def test_a_tab_cannot_smuggle_an_argument_past_the_git_rules(tmp_path, command):
    assert not check(tmp_path, "Bash", command).allowed
    assert not policy.ToolPolicy(tmp_path, "fp1").check("Bash", {"command": command}).allowed


@pytest.mark.parametrize("command", CONTROL_WHITESPACE)
def test_the_git_rules_refuse_tab_and_the_ascii_whitespace_controls(tmp_path, command):
    assert not check(tmp_path, "Bash", command).allowed


@pytest.mark.parametrize("command", [*REFUSED_BASH, *REFUSED_BASH_ROUND2, *REFUSED_BASH_ROUND3, *ABBREVIATIONS])
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
    """The rules cannot know that `backend/link` is a symlink or what a test run executes: they allow the
    `git add`; the runner's diff gate refuses the symlink and every protected path (test_publisher.py,
    test_publisher_real_git.py). Stated here so the gap is visible, not hidden. A protected path as such
    IS now refused by the rules (REFUSED_BASH)."""
    assert check(tmp_path, "Bash", "git add backend/link").allowed
    # `?` and `[` globs are not refused by the generated rules (a `?` deny rule could be read as a wildcard by the
    # CLI and refuse every add); ToolPolicy refuses them, and the diff gate is what stops a protected result.
    for glob in ("git add responder/vt_responde?/x.py", "git add backend/[.]github/x"):
        assert check(tmp_path, "Bash", glob).allowed
        assert not policy.ToolPolicy(tmp_path, "fp1").check("Bash", {"command": glob}).allowed
    assert not check(tmp_path, "Bash", "git add .github/workflows/x.yml").allowed
    assert not policy.ToolPolicy(tmp_path, "fp1").check("Bash", {"command": "git add .github/workflows/x.yml"}).allowed
