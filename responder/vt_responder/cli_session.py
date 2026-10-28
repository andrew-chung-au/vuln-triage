"""The headless ``claude -p`` session behind the ``AgentSession`` seam (#260, amends F2).

One ``claude -p`` process per alert, run from the fresh checkout, on the owner's Claude login (no
API key). The agent only commits locally; the RUNNER checks the commits, pushes and opens the
pull request (``publisher.py``), so no git credential is ever in the agent's environment.

What was verified, and from where, is in ``_docs/responder-cli-runtime.md``. In short, from
``claude --help`` (2.1.311) and code.claude.com/docs (headless, cli-reference, permissions,
authentication), read 2026-10-27 and never run against a login or a model:
* ``-p`` reads the prompt from stdin; ``--output-format json`` prints one result object with
  ``result``, ``is_error``, ``subtype``, ``num_turns``; ``--max-turns`` ends a run with an error;
* ``--permission-mode dontAsk`` denies whatever is not allowed, so a headless run never waits;
* ``--tools``, ``--allowedTools`` and ``--disallowedTools`` are variadic, so they are passed as one
  comma-joined value each and the task goes on stdin (``cli_rules.CliToolRules.argv``);
* ``claude auth status`` exits 0 when logged in and 1 when not, and needs no model call.

The process is started in its own session (process group) and killed as a group on the time limit;
every process also carries ``VT_RUN_MARKER`` so the runner can stop stragglers (``procs.py``).
Output goes to files in a temporary directory OUTSIDE the checkout and is deleted afterwards; only
the exit code, turn count and a failure code are logged, plus (on a failed run) a short snippet of the
agent's final message: the ``RESULT: ESCALATE`` text, or the last characters of the message when there
is no ``RESULT:`` line or the CLI reported an error. The runner redacts and caps it; stderr is never logged.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping

from .cli_rules import CliToolRules, build_rules
from .config import ConfigError
from .envscrub import cli_env
from .procs import MARKER_VAR
from .real_runner import AgentResult, RunContext

BINARY = "claude"
# Flags the run relies on that `claude --help` lists (2.1.311). `--max-turns` is documented in the
# CLI reference but is NOT in that help text, so it cannot be checked here: VERIFY at the first live run.
REQUIRED_HELP_FLAGS = (
    "--print", "--model", "--output-format", "--permission-mode", "--allowedTools", "--disallowedTools",
    "--tools", "--append-system-prompt", "--no-session-persistence", "--safe-mode",
)
# `claude auth status` reports how it would authenticate. Only a subscription login is wanted here:
# anything else (an API key, a key helper, a cloud provider) may bill something other than the plan.
PLAN_AUTH_METHODS = ("claude.ai", "oauth_token")
_MAX_OUTPUT_BYTES = 5_000_000  # per output file; more is a failed run (checked while the CLI runs, and after)
_POLL_SECONDS = 0.25
_TEXT_REASONS = ("agent_cli_error", "result_line_missing", "agent_escalated")
# Windows of agent text handed to the runner. The runner redacts a whole window, then keeps the first
# (RESULT: line text) or last (final-message tail) real_runner.MAX_FAILURE_TEXT characters of it.
_MAX_HEAD = 800
_MAX_TAIL = 800
_RESULT_LINE = re.compile(r"^RESULT:\s*(FIXED|FALSE_POSITIVE|ESCALATE)\b[ \t]*(.*)$", re.MULTILINE)
# VERIFY: exact wording. The errors page lists "You've hit your session/weekly/Opus/Sonnet limit"; the
# exit code and JSON shape of a headless run that hits one are not documented there.
_USAGE_LIMIT = re.compile(r"hit your .{0,30}limit|usage limit|rate.limit|credit balance", re.IGNORECASE)
GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "VulnTriage responder", "GIT_COMMITTER_NAME": "VulnTriage responder",
    "GIT_AUTHOR_EMAIL": "responder@users.noreply.github.com",
    "GIT_COMMITTER_EMAIL": "responder@users.noreply.github.com",
    "GIT_TERMINAL_PROMPT": "0",
}


def _which(environ: Mapping[str, str], binary: str) -> str | None:
    return shutil.which(binary, path=environ.get("PATH", os.defpath))


def _probe(argv: list[str], env: dict[str, str], timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(argv, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                          timeout=timeout, check=False)


def preflight(environ: Mapping[str, str] | None = None, *, binary: str = BINARY, timeout: float = 30.0) -> str:
    """Start-up check: the ``claude`` binary exists, supports the flags used, and is logged in with a
    subscription login. Returns the auth method; raises ``ConfigError`` with a clear message. No model call.

    It runs with the SAME scrubbed environment as a run (``cli_env``), so an ``ANTHROPIC_API_KEY`` set
    on the responder cannot make it look logged in.
    """
    environ = os.environ if environ is None else environ
    env = cli_env(environ)
    path = _which(env, binary)
    if path is None:
        raise ConfigError("the 'claude' CLI is not on PATH: install Claude Code on the responder host "
                          "(RESPONDER_RUNTIME=cli runs `claude -p` on your login)")
    try:
        helped = _probe([path, "--help"], env, timeout)
        status = _probe([path, "auth", "status"], env, timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ConfigError(f"the 'claude' CLI could not be probed ({type(exc).__name__})") from None
    missing = [flag for flag in REQUIRED_HELP_FLAGS if flag not in helped.stdout]
    if helped.returncode != 0 or missing:
        raise ConfigError("the 'claude' CLI is too old or not Claude Code: its --help lacks "
                          + (", ".join(missing) or "output"))
    method = ""
    logged_out = False
    try:
        data = json.loads(status.stdout)
        method = str(data.get("authMethod", "")) if isinstance(data, dict) else ""
        logged_out = isinstance(data, dict) and data.get("loggedIn") is False
    except ValueError:
        pass
    if status.returncode != 0 or logged_out:
        raise ConfigError("the 'claude' CLI is not logged in: run `claude auth login` as the user "
                          "that runs the responder")
    if method not in PLAN_AUTH_METHODS:
        # method is a short fixed word from the CLI; shown so the owner can see why it was refused
        shown = method if re.fullmatch(r"[A-Za-z0-9_.-]{1,30}", method) else "unknown"
        raise ConfigError(f"the 'claude' CLI authenticates by '{shown}', not a subscription login: "
                          "run `claude auth login` with your Claude account")
    return method


def _tail(body: str) -> str | None:
    """The last ``_MAX_TAIL`` printable characters of the final message, whitespace collapsed, for the
    failure log. Untrusted text: the runner redacts it, keeps the last 500 characters and logs it
    JSON-encoded. It is longer than what is kept so a secret cut by this window is redacted whole first."""
    flat = " ".join("".join(c if c.isprintable() else " " for c in body).split())
    return flat[-_MAX_TAIL:].strip() or None


def parse_output(text: str, model: str) -> AgentResult:
    """The result of a finished run from the ``--output-format json`` object. Anything not clearly a
    success with a ``RESULT:`` line is an error with a short reason code (a failed run)."""
    try:
        data: Any = json.loads(text)
    except ValueError:
        return AgentResult("error", model, reason="output_unparseable")
    if isinstance(data, list):  # a stream: the last result object
        data = next((d for d in reversed(data) if isinstance(d, dict) and d.get("type") == "result"), None)
    if not isinstance(data, dict):
        return AgentResult("error", model, reason="output_unparseable")
    body = data.get("result") if isinstance(data.get("result"), str) else ""
    served = model
    usage = data.get("modelUsage")  # VERIFY: key name; falls back to the configured model
    if isinstance(usage, dict) and usage:
        first = str(next(iter(usage)))
        if re.fullmatch(r"[A-Za-z0-9_.:\[\]-]{1,80}", first):
            served = first
    if data.get("is_error") or data.get("subtype") not in (None, "success"):
        if _USAGE_LIMIT.search(body):
            return AgentResult("error", served, reason="plan_usage_limit")
        if data.get("subtype") == "error_max_turns":
            return AgentResult("error", served, reason="max_turns")
        return AgentResult("error", served, reason="agent_cli_error", explanation=_tail(body))
    found = _RESULT_LINE.findall(_outside_fences(body))
    if not found:
        return AgentResult("error", served, reason="result_line_missing", explanation=_tail(body))
    kind, rest = found[-1]
    # A wider window than anything logs or publishes: the runner redacts the whole window FIRST and
    # only then cuts it (to 500 characters), so a secret straddling the final cut is never half-kept.
    summary = "".join(c for c in rest if c.isprintable())[:_MAX_HEAD].strip() or None
    if kind == "FIXED":
        return AgentResult("fixed", served, explanation=summary)
    if kind == "FALSE_POSITIVE":
        return AgentResult("no_change", served, explanation=summary)
    return AgentResult("error", served, reason="agent_escalated", explanation=summary)  # why, for the log


def _too_big(*paths: Path) -> bool:
    try:
        return any(p.stat().st_size > _MAX_OUTPUT_BYTES for p in paths)
    except OSError:
        return False


def _outside_fences(body: str) -> str:
    """``body`` without fenced code blocks (``` or ~~~; an unclosed fence runs to the end): a ``RESULT:`` line
    the agent quoted from a file or a log is not its verdict."""
    kept: list[str] = []
    fence: str | None = None  # the opening run, e.g. "````" or "~~~"
    for line in body.splitlines():
        if fence is None:
            opening = re.match(r"\s*(`{3,}|~{3,})", line)  # lenient: any indent, any info string (hides more, not less)
            if opening:
                fence = opening.group(1)
            else:
                kept.append(line)
        elif re.fullmatch(r"\s*" + fence[0] + "{" + str(len(fence)) + r",}\s*", line):
            fence = None  # closed by the same character, at least as long, nothing else on the line
    return "\n".join(kept)


def _kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)  # its own group (start_new_session), never ours
    except OSError:
        pass


class CliSession:
    """One headless ``claude -p`` run for one alert."""

    def __init__(self, model: str, ctx: RunContext, *, environ: Mapping[str, str] | None = None,
                 binary: str = BINARY, rules: CliToolRules | None = None,
                 output_root: Path | None = None) -> None:
        if ctx.checkout is None:
            raise RuntimeError("a live session needs a fresh checkout")
        self._model = model
        self._ctx = ctx
        self._environ = os.environ if environ is None else environ
        self._binary = binary
        self._rules = rules or build_rules()
        self._output_root = output_root

    def argv(self, system_prompt: str, binary_path: str) -> list[str]:
        return [
            binary_path, "-p", "--model", self._model, "--max-turns", str(self._ctx.max_turns),
            "--output-format", "json", "--permission-mode", "dontAsk", "--no-session-persistence",
            "--safe-mode", *self._rules.argv(), "--append-system-prompt", system_prompt,
        ]

    def environment(self) -> dict[str, str]:
        return cli_env(self._environ, {**GIT_IDENTITY, MARKER_VAR: self._ctx.run_marker})

    def run(self, system_prompt: str, task: str) -> AgentResult:
        env = self.environment()
        path = _which(env, self._binary)
        if path is None:
            raise FileNotFoundError("claude")
        out_dir = Path(tempfile.mkdtemp(prefix="vt-cli-", dir=None if self._output_root is None
                                        else str(self._output_root)))
        try:
            stdout_path, stderr_path = out_dir / "stdout.json", out_dir / "stderr.txt"
            with open(stdout_path, "wb") as out, open(stderr_path, "wb") as err:
                proc = subprocess.Popen(self.argv(system_prompt, path), cwd=self._ctx.checkout, env=env,
                                        stdin=subprocess.PIPE, stdout=out, stderr=err,
                                        start_new_session=True)
                try:
                    try:
                        assert proc.stdin is not None
                        proc.stdin.write(task.encode())
                        proc.stdin.close()
                    except OSError:
                        pass  # the process ended early; its exit code tells the story
                    deadline = time.monotonic() + max(self._ctx.timeout_seconds, 0.1)
                    while True:  # poll, so a run that floods its output is stopped while it runs
                        try:
                            code = proc.wait(timeout=max(min(_POLL_SECONDS, deadline - time.monotonic()), 0.01))
                            break
                        except subprocess.TimeoutExpired:
                            if _too_big(stdout_path, stderr_path):
                                _kill_group(proc.pid)
                                proc.wait()
                                return AgentResult("error", self._model, reason="output_too_large")
                            if time.monotonic() >= deadline:
                                _kill_group(proc.pid)
                                proc.wait()
                                raise TimeoutError("claude -p exceeded the run's time limit") from None
                finally:
                    if proc.poll() is None:  # any other exit path: do not leave it running
                        _kill_group(proc.pid)
                        proc.wait()
            if _too_big(stdout_path, stderr_path):  # never a truncated read of a valid result
                return AgentResult("error", self._model, reason="output_too_large")
            raw = stdout_path.read_bytes()[:_MAX_OUTPUT_BYTES].decode("utf-8", "replace")
            if code != 0:
                limited = _USAGE_LIMIT.search(raw) or _USAGE_LIMIT.search(
                    stderr_path.read_bytes()[:_MAX_OUTPUT_BYTES].decode("utf-8", "replace"))
                if limited:
                    return AgentResult("error", self._model, reason="plan_usage_limit")
                parsed = parse_output(raw, self._model)
                if parsed.reason == "max_turns":
                    return AgentResult("error", self._model, reason="max_turns")
                # a non-zero exit is never a success; stdout's final message (not stderr) says why
                return AgentResult("error", self._model, reason="cli_exit_nonzero",
                                   explanation=parsed.explanation if parsed.reason in _TEXT_REASONS else None)
            return parse_output(raw, self._model)
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)
