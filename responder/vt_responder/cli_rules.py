"""The ``claude -p`` allow and deny rules, generated from ``policy.py`` (#260).

One source: the writable roots, protected components, suffixes, lockfiles, make targets and
git subcommands all come from ``policy`` constants, so a change there changes the rules.

The CLI runs headless with ``--permission-mode dontAsk`` (anything not allowed is denied,
nothing prompts), so the allow list below is the whole grant. Reads inside the checkout need
no rule (a bare ``Read`` allow would also reach files OUTSIDE it, such as the login under
``HOME``, so it is deliberately absent). Rule syntax and precedence were read from
code.claude.com/docs/en/permissions on 2026-10-27 and are written up in
``_docs/responder-cli-runtime.md``: deny is evaluated first and always wins; ``Bash(x *)`` is a
prefix rule; ``Edit(dir/**)`` is anchored at the working directory.

What a CLI rule CANNOT express (so the runner's diff gate, ``publisher.py``, is the control):
* the arguments of ``git add`` and ``git commit`` are constrained only by prefix and substring
  patterns (an allow per writable root, ``git commit -m *``, deny patterns for flags and protected
  names; see ``_git_denials``). The docs call argument-constraining Bash rules fragile, so this is
  best effort: a path the patterns do not know, or a differently cased protected name, is left to
  the diff gate;
* a program invoked in another form: ``/usr/bin/curl``, ``sh -c 'curl ...'``,
  ``git -C . push`` are not matched by ``Bash(curl *)`` / ``Bash(git push *)``. They are not
  ALLOWED either (dontAsk denies them), but code the agent writes into a test and ``make test``
  runs is not seen by any rule;
* case-insensitive path matching (the gate is case-insensitive, the rules are not);
* ``?``, ``[`` and ``]`` globs in ``git add`` (not refused; the diff gate refuses the result). ``$``, ``{`` and ``}`` ARE
  refused in the git arguments (``GIT_EXPANSION``), because shell expansion rebuilds a denied flag after the rules look.

``evaluate`` below is this repository's MODEL of the documented semantics, used by the tests to
check every refused case against the generated list. The CLI itself is the authority; the model
being right about it is a ``VERIFY:`` item for the first live run.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .policy import (
    CLI_GIT_READ,
    KNOWN_TOOLS,
    MAKE_TARGETS,
    PROTECTED_COMPONENTS,
    PROTECTED_LOCKFILES,
    PROTECTED_PATH_PREFIXES,
    PROTECTED_SUFFIXES,
    READ_TOOLS,
    WRITABLE_ROOTS,
    Decision,
)

# Commands the policy refuses outright; written as explicit deny rules too so a later widening of
# the allow list cannot silently allow them (deny always wins).
DENIED_COMMANDS = (
    "git push", "gh", "curl", "wget", "ssh", "scp", "sudo", "pip", "pip3", "uv", "uvx", "npm",
    "npx", "node", "pytest", "python", "python3", "git config", "git remote", "git checkout",
    "git switch", "git branch", "git reset", "git rebase", "git merge", "git tag", "git fetch",
    "git pull", "git clone",
)
DENIED_MAKE = ("make *install*",)
DENIED_TOOLS = ("WebFetch", "WebSearch")


@dataclass(frozen=True)
class CliToolRules:
    tools: tuple[str, ...]  # --tools: the built-in set the agent has at all
    allowed: tuple[str, ...]  # --allowedTools
    denied: tuple[str, ...]  # --disallowedTools

    def argv(self) -> list[str]:
        """Flag/value pairs, each list joined into ONE value: ``--allowedTools``, ``--disallowedTools``
        and ``--tools`` take variadic values, so a prompt (or any flag) after a list could be
        swallowed; the task is sent on stdin and no rule contains a comma."""
        return ["--tools", ",".join(self.tools), "--allowedTools", ",".join(self.allowed),
                "--disallowedTools", ",".join(self.denied)]


# Abbreviated on purpose: git accepts unambiguous prefixes of long options. ``--ou`` covers ``--output``
# (writes a file outside the checkout), ``--no-i`` covers ``--no-index`` (reads outside it), ``--ext`` and
# ``--text`` cover ``--ext-diff`` / ``--textconv`` (run external programs). ToolPolicy refuses every flag
# outside its short read list; these are the same refusals for the prefix rules.
GIT_READ_DENIED_FLAGS = ("--ou", "--no-i", "--ext", "--text", "--or", "-O")
# The long options behind those substrings. git also accepts any UNAMBIGUOUS prefix; every prefix of these (three
# characters or more) is denied as a whole argument too (an ambiguous one is an error in git anyway).
GIT_READ_DENIED_LONG = ("--output", "--no-index", "--ext-diff", "--textconv", "--orderfile")
# Quote and backslash split a flag the substring patterns match on (``--o"utput=x"`` runs as ``--output=x``). In a rule,
# ``\\`` is a literal backslash and ``\*`` a literal asterisk (VERIFY: the CLI's escape syntax; if it differs these
# rules are inert and ToolPolicy and the diff gate are what refuse the forms).
GIT_QUOTE_AND_BACKSLASH = ('"', "'", "\\\\")
# Shell expansion: ``$`` (``--${u}output=x`` runs as ``--output=x`` when ``u`` is unset) and brace expansion (``{a,b}``)
# rebuild a denied flag or a protected path AFTER the rules matched the raw text, so the three characters are refused
# in every argument of ``git status|diff|log|add|commit`` (ToolPolicy refuses them as shell metacharacters). ``$(`` and
# backticks are handled separately: the inner command is checked as a subcommand. ``?``, ``[`` and ``]`` are not
# refused here (a ``?`` in a rule may be read as a wildcard); see the module docstring.
GIT_EXPANSION = ("$", "{", "}")
# Flags that must not follow ``git commit -m <msg>``. ``git commit * -*`` below refuses any flag after the first
# argument (including abbreviations such as ``--am`` and ``--no-ver``) and ``--``; these named ones stay as a record.
GIT_COMMIT_DENIED_FLAGS = (
    "--amend", "--no-verify", "--all", "--allow-empty", "--author", "--date", "--file", "--template", "--fixup",
    "--squash", "--reuse-message", "--reedit-message", "--no-edit", "--interactive", "--patch", "--include",
    "--only", "--signoff", "--gpg-sign", "--no-gpg-sign",
)


def _git_denials() -> list[str]:
    denied = [f"Bash(git {sub} *{flag}*)" for sub in CLI_GIT_READ for flag in GIT_READ_DENIED_FLAGS]
    for sub in CLI_GIT_READ:
        for option in GIT_READ_DENIED_LONG:
            for size in range(3, len(option) + 1):
                prefix = option[:size]
                denied += [f"Bash(git {sub} *{prefix})", f"Bash(git {sub} *{prefix} *)", f"Bash(git {sub} *{prefix}=*)"]
        denied += [f"Bash(git {sub} *{char}*)" for char in GIT_QUOTE_AND_BACKSLASH + GIT_EXPANSION]
    # git add: no flag anywhere (-A, -u, -f, --force, --all, ``--``), no ".", no "..", no absolute path, no quote,
    # backslash, tab or ``*`` (they split or expand a protected name after the rule has looked at the text), and no
    # protected component, suffix, lockfile or the responder's own code in ANY argument.
    denied += ["Bash(git add -*)", "Bash(git add * -*)", "Bash(git add .)", "Bash(git add . *)",
               "Bash(git add * .)", "Bash(git add *..*)", "Bash(git add /*)", "Bash(git add * /*)",
               "Bash(git add *.env*)", "Bash(git add *Dockerfile*)", "Bash(git add *\t*)", "Bash(git add *\\**)"]
    denied += [f"Bash(git add *{char}*)" for char in GIT_QUOTE_AND_BACKSLASH + GIT_EXPANSION]
    denied += [f"Bash(git commit *{char}*)" for char in GIT_EXPANSION]  # same refusal as ToolPolicy's shell-metacharacter one
    for extension in (".yaml", ".yml"):  # the policy's protected ``compose*.yaml`` / ``compose*.yml``
        denied += [f"Bash(git add *compose*{extension})", f"Bash(git add *compose*{extension} *)"]
    for component in sorted(PROTECTED_COMPONENTS):
        denied += [f"Bash(git add {component}/*)", f"Bash(git add */{component}/*)", f"Bash(git add * {component}/*)"]
    for suffix in sorted(PROTECTED_SUFFIXES):
        denied += [f"Bash(git add *{suffix})", f"Bash(git add *{suffix} *)"]
    for name in sorted(PROTECTED_LOCKFILES):
        denied += [f"Bash(git add *{name})", f"Bash(git add *{name} *)"]
    denied += [f"Bash(git add *{prefix}*)" for prefix in PROTECTED_PATH_PREFIXES]
    denied += [f"Bash(git commit *{flag}*)" for flag in GIT_COMMIT_DENIED_FLAGS]
    # ONE quoted message and nothing else: any flag or ``--`` after the first argument, and any quote followed by a
    # space (a second argument after the message), are refused. A message containing " -" or "' " is refused too.
    denied += ["Bash(git commit * -*)", "Bash(git commit *' *)", 'Bash(git commit *" *)']
    return denied


def build_rules() -> CliToolRules:
    tools = tuple(sorted(KNOWN_TOOLS))
    allowed: list[str] = [f"Edit({root}/**)" for root in sorted(WRITABLE_ROOTS)]
    allowed += [f"Bash(make {target})" for target in sorted(MAKE_TARGETS)]
    allowed += [f"Bash(git {sub} *)" for sub in CLI_GIT_READ]
    # ``git add`` only with a path that starts under a writable root; ``git commit`` only as ``-m <message>``.
    # Anything else (``-A``, ``.``, ``--force``, ``-am``, ``--amend``) matches no allow rule, so dontAsk refuses it.
    allowed += [f"Bash(git add {root}/*)" for root in sorted(WRITABLE_ROOTS)]
    allowed += ["Bash(git commit -m '*')", 'Bash(git commit -m "*")']  # one quoted message (VERIFY: CLI quote handling)

    denied: list[str] = list(DENIED_TOOLS)
    denied += _git_denials()
    denied += [f"Bash({cmd} *)" for cmd in DENIED_COMMANDS]
    denied += [f"Bash({pattern})" for pattern in DENIED_MAKE]
    denied.append("Bash(*merge*)")  # policy: any command mentioning "merge" is refused
    denied += [f"Edit(**/{component}/**)" for component in sorted(PROTECTED_COMPONENTS)]
    denied += [f"Edit(**/*{suffix})" for suffix in sorted(PROTECTED_SUFFIXES)]
    denied += ["Edit(**/.env*)", "Edit(**/Dockerfile*)", "Edit(**/compose*.yaml)", "Edit(**/compose*.yml)"]
    denied += [f"Edit(**/{name})" for name in sorted(PROTECTED_LOCKFILES)]
    denied += [f"Edit({prefix}**)" for prefix in PROTECTED_PATH_PREFIXES]
    denied += ["Read(**/.env*)", "Read(!**/.env.example)"]  # a later "!" carves the example back out
    return CliToolRules(tools, tuple(allowed), tuple(denied))


# -- the model of the documented rule semantics (tests only; the CLI is the authority) -----------

_RULE = re.compile(r"^(?P<tool>[A-Za-z]+)(?:\((?P<arg>.*)\))?$", re.DOTALL)
_SEPARATORS = re.compile(r"&&|\|\||\|&|[;|&\n]")


@lru_cache(maxsize=None)
def _glob(pattern: str) -> "re.Pattern[str]":
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out), re.DOTALL)


@lru_cache(maxsize=None)
def _command_pattern(pattern: str) -> "re.Pattern[str]":
    # ``*`` is a wildcard; ``\*`` and ``\\`` are a literal asterisk and backslash (VERIFY: the CLI's escape syntax).
    parts, i = [""], 0
    while i < len(pattern):
        if pattern[i] == "\\" and pattern[i + 1:i + 2] in ("*", "\\"):
            parts[-1] += pattern[i + 1]
            i += 2
        elif pattern[i] == "*":
            parts.append("")
            i += 1
        else:
            parts[-1] += pattern[i]
            i += 1
    # "* " at the end also matches the bare command when it is the only wildcard.
    bare = len(parts) == 2 and parts[1] == "" and parts[0].endswith(" ")
    if bare:
        parts = [parts[0][:-1]]
    return re.compile(".*".join(re.escape(part) for part in parts) + ("(?: .*)?" if bare else ""), re.DOTALL)


def _matches(rule: str, tool: str, arg: str) -> bool:
    found = _RULE.match(rule)
    if not found or found.group("tool") != tool:
        return False
    pattern = found.group("arg")
    if pattern is None:
        return True  # the tool name alone matches every use
    if tool == "Bash":
        return _command_pattern(pattern).fullmatch(arg) is not None
    return _glob(pattern.removeprefix("!")).fullmatch(arg) is not None


def _denied(rules: CliToolRules, tool: str, arg: str) -> bool:
    hit = False
    for rule in rules.denied:  # order matters only for the "!" carve-outs
        found = _RULE.match(rule)
        negation = bool(found and (found.group("arg") or "").startswith("!"))
        if _matches(rule, tool, arg):
            hit = not negation
    return hit


def _relative(checkout: Path, raw: str) -> str | None:
    root = os.path.normpath(str(checkout))
    full = os.path.normpath(raw if os.path.isabs(raw) else os.path.join(root, raw))
    if full == root or not full.startswith(root + os.sep):
        return None
    return Path(full).relative_to(root).as_posix()


def evaluate(rules: CliToolRules, checkout: Path, tool: str, arg: str) -> Decision:
    """Allow or deny one tool use under ``dontAsk``: deny rules first, then allow rules, then the
    default (reads inside the checkout run; everything else is denied)."""
    if tool not in rules.tools:
        return Decision.deny("tool_not_available")
    if tool == "Bash":
        if re.search(r"[<>]", arg):
            return Decision.deny("redirection_not_modelled")  # the CLI checks targets against Edit rules
        # Substitutions and subshells: the inner commands are checked as subcommands too.
        flattened = arg.replace("$(", ";").replace("`", ";").replace("(", ";").replace(")", ";")
        parts = [p.strip() for p in _SEPARATORS.split(flattened) if p.strip()]
        if not parts:
            return Decision.deny("command_not_allowed")
        for part in parts:  # a deny rule applies if ANY subcommand matches; allow needs EACH to match
            if _denied(rules, "Bash", part):
                return Decision.deny("denied_by_rule")
        if all(any(_matches(r, "Bash", p) for r in rules.allowed) for p in parts):
            return Decision.ok()
        return Decision.deny("not_allowed")
    rel = _relative(checkout, arg) if arg else ""
    if rel is None:
        return Decision.deny("path_outside_checkout")
    if _denied(rules, "Read" if tool in READ_TOOLS else "Edit", rel):
        return Decision.deny("denied_by_rule")
    if tool in READ_TOOLS:
        return Decision.ok()
    if any(_matches(r, "Edit", rel) for r in rules.allowed):
        return Decision.ok()
    return Decision.deny("not_allowed")
