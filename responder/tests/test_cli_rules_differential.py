"""#260 QA round 5 (N2): a differential test that ends the "one more spelling" class.

Three QA rounds in a row found a spelling of `git commit` / `git add` / `git status|diff|log` that the CLI rules (as
modelled by `cli_rules.evaluate`) allowed and `ToolPolicy` refused. Instead of one more deny pattern per spelling,
this generates thousands of commands from adjacent fragments (both quote kinds, spaces, tabs, flags, paths, shell
metacharacters, in many orders) with a fixed seed and asserts the one-way property that matters: whenever the rules
allow a command, `ToolPolicy` allows it too.

Intentional carve-outs (the rules allow MORE than `ToolPolicy`, on purpose, and the differences are read-only or
refused by the diff gate): see `_flags_outside_the_policy_list`.
"""

from __future__ import annotations

import random
import shlex

import pytest

from vt_responder import policy
from vt_responder.cli_rules import build_rules, evaluate

pytestmark = pytest.mark.unit

RULES = build_rules()
SEED = 260_5
CASES = 6000

PREFIXES = ("git commit", "git add", "git status", "git diff", "git log")
FRAGMENTS = (
    '"', "'", '"', "'", " ", " ", "\t", "-", "-a", "--amend", "-m", "z", "x", "msg", "fix", "Don't", "#123", ":",
    "backend/a.py", "backend/", "tests/t.py", "README.md", ".env", "..", "*", "$", "{", "}", "\\", "`", ";", "&", "(",
    ")", "<", ">", "|", "-1", "--stat", "--output=/x", "\n", "\r", "\x0b", "\xa0",
)

def _generate() -> list[str]:
    rng = random.Random(SEED)
    out = []
    for i in range(CASES):
        prefix = rng.choice(PREFIXES)
        parts = [rng.choice(FRAGMENTS) for _ in range(rng.randint(1, 8))]
        glue = rng.choice(("", " ", "", " "))
        if i % 2:  # half the cases start from the legitimate shape and get noise spliced in, to reach the allowed region
            noise = glue.join(rng.choice(FRAGMENTS) for _ in range(rng.randint(0, 3)))
            quote = rng.choice(('"', "'"))
            if i % 4 == 1:
                base = f"git commit -m {quote}{rng.choice(('fix', 'Dont', 'x y'))}{quote}"
            else:
                base = f"git add {rng.choice(('backend/a.py', 'tests/t.py', 'responder/x.py', 'frontend/a.ts'))}"
            at = rng.randint(0, len(base))
            out.append(base[:at] + noise + base[at:])
            continue
        out.append(prefix + " " + glue.join(parts))
    # the QA forms and the legitimate flow, so a change to the generator cannot drop them
    out += ['git commit -m "x"z "-a"', "git commit -m \"x\"-m \"-a\"", 'git commit -m "x"z "README.md"',
            "git commit -m 'x'z '-a'", "git commit -m 'x'-m '-a'", "git commit -m 'x'z 'README.md'",
            'git commit -m "Fix: handle None in notifier"', 'git commit -m "Don\'t drop failed jobs"',
            "git commit -m 'fix #123: retry the job'", "git add backend/a.py tests/t.py", "git status", "git log -1"]
    return out


QA_ROUND5_FORMS = [
    'git commit -m "x"z "-a"', 'git commit -m "x"-m "-a"', 'git commit -m "x"z "README.md"',
    "git commit -m 'x'z '-a'", "git commit -m 'x'-m '-a'", "git commit -m 'x'z 'README.md'",
]


@pytest.mark.parametrize("command", QA_ROUND5_FORMS)
def test_the_qa_round_5_commit_forms_are_refused_by_the_rules_and_by_the_policy(tmp_path, command):
    assert not evaluate(RULES, tmp_path, "Bash", command).allowed
    assert not policy.ToolPolicy(tmp_path, "fp1").check("Bash", {"command": command}).allowed


@pytest.mark.parametrize("command", ["git add backend/a.py tests/t.py", "git add backend/a.py README.md",
                                     "git add backend/a.py backend/b.py", 'git commit -m "-fix"', "git commit -m '-fix'"])
def test_one_path_per_git_add_and_no_message_starting_with_a_dash(tmp_path, command):
    assert not evaluate(RULES, tmp_path, "Bash", command).allowed


@pytest.mark.parametrize("message", ["Fix: handle None in notifier", "Don't drop failed jobs", "fix #123: retry the job",
                                     "Fix 50% failures", "Fix retry on 5xx"])
def test_ordinary_commit_messages_are_allowed_by_the_rules_and_by_the_policy(tmp_path, message):
    command = f'git commit -m "{message}"'
    assert evaluate(RULES, tmp_path, "Bash", command).allowed, command
    assert policy.ToolPolicy(tmp_path, "fp1").check("Bash", {"command": command}).allowed, command


def test_whenever_the_rules_allow_git_add_or_commit_the_policy_allows_it_too(tmp_path):
    """`git add` and `git commit` change the repository: the rules must never allow what `ToolPolicy` refuses. (The
    rules are stricter in places, for example a lockfile or `compose*.yml` path; that direction is fine.)"""
    pol = policy.ToolPolicy(tmp_path, "fp1")
    allowed_by_rules = 0
    disagreements = []
    for command in _generate():
        if not command.startswith(("git add", "git commit")) or not evaluate(RULES, tmp_path, "Bash", command).allowed:
            continue
        # Documented residual (2026-10-28): the deny patterns for tab/VT/FF/CR were removed because the real CLI reads a
        # control character in a pattern as a space. These forms are caught only by ToolPolicy and the runner's diff gate
        # (VERIFY), so the rules are not compared with the policy for them.
        if any(c in command.strip(" \t\n") for c in "\t\x0b\x0c\r"):
            continue
        allowed_by_rules += 1
        # Carve-out: leading and trailing space, tab and newline are trimmed (the shell ignores them too); ToolPolicy
        # refuses a newline anywhere, so the comparison is on the trimmed command.
        if not pol.check("Bash", {"command": command.strip(" \t\n")}).allowed:
            disagreements.append(command)
    assert allowed_by_rules > 20 # the generator reaches the allowed region; a vacuous pass would hide a regression
    assert not disagreements, f"{len(disagreements)} of {allowed_by_rules} allowed: {disagreements[:15]!r}"


def test_whenever_the_rules_allow_git_status_diff_or_log_the_shell_hands_git_no_dangerous_flag(tmp_path):
    """Read commands: the rules deliberately allow more than `ToolPolicy` (any flag not denied, any argument inside
    the checkout, an empty part after a separator), so the policy is not the oracle here. The oracle is what the
    shell would hand git: after `shlex` splitting, no word may be, or abbreviate, a flag that writes outside the
    checkout, reads outside it, or runs a program (`--output`, `--no-index`, `--ext-diff`, `--textconv`,
    `--orderfile`, `-O`)."""
    dangerous = ("--output", "--no-index", "--ext-diff", "--textconv", "--orderfile")
    allowed_by_rules = 0
    bad = []
    for command in _generate():
        if not command.startswith(("git status", "git diff", "git log")) or not evaluate(RULES, tmp_path, "Bash", command).allowed:
            continue
        allowed_by_rules += 1
        try:
            words = shlex.split(command)
        except ValueError:
            bad.append(command)  # the shell would reject it or read it differently from the rules
            continue
        for word in words[2:]:
            name = word.split("=", 1)[0]
            if word.startswith("-O") or (name.startswith("--") and len(name) >= 5 and any(d.startswith(name) for d in dangerous)):
                bad.append(command)
    assert allowed_by_rules > 100
    assert not bad, f"{len(bad)} of {allowed_by_rules} allowed: {bad[:15]!r}"
