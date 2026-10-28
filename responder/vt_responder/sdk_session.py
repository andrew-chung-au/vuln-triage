"""The live Claude Agent SDK session behind the ``AgentSession`` seam (#221).

The SDK (``claude_agent_sdk``, the responder-only dependency approved in F2) is
imported lazily, inside ``SdkSession.run``; importing this module imports no
SDK. It cannot be run live without ``ANTHROPIC_API_KEY`` and a GitHub token, so
the tests drive it with a fake SDK object and one test builds the real
``ClaudeAgentOptions`` (no connection) to catch a misspelt option.

How the allowlist is enforced (two layers, one policy: ``policy.ToolPolicy``):
* a ``PreToolUse`` hook runs for EVERY tool call (built-in read tools included,
  which the CLI otherwise allows without asking) and denies what the policy
  refuses;
* ``can_use_tool`` runs for calls that would prompt (Edit, Write, Bash) and
  allows only what the policy allows.
``tools`` also limits the built-in tool set, and ``permission_mode`` stays
``default`` with no ``allowed_tools`` so nothing is pre-approved around them.

Limit: this policy guards a confused agent, not a hostile or prompt-injected one; the
agent's own model key and git token stay visible to the code it runs. What bounds a
hostile agent, and the owner's accepted residual risk, is in
``_docs/responder-security-limits.md``.

The agent ends its final message with one line, ``RESULT: PULL_REQUEST <url>``
or ``RESULT: NO_CHANGE <explanation>`` (see ``prompt.py``); anything else, an
error result, or hitting the turn limit is an ``error``.

VERIFY (against claude-agent-sdk 0.2.174, read from the installed package; not
run live): ``ClaudeSDKClient`` as an async context manager with ``query`` and
``receive_response``; ``ClaudeAgentOptions`` fields used below; ``HookMatcher``;
``PermissionResultAllow``/``PermissionResultDeny``; ``AssistantMessage.model``;
``ResultMessage.is_error/subtype/result``; and that a ``PreToolUse`` hook
returning ``permissionDecision: "deny"`` overrides the permission mode.
"""

from __future__ import annotations

import asyncio
import importlib
import os
import re
from typing import Any, Mapping, Sequence

from .actlog import ActionLog
from .checkout import git_auth_env
from .envscrub import blank_non_allowlisted, redacted_window
from .procs import MARKER_VAR
from .policy import KNOWN_TOOLS, Decision, ToolPolicy
from .real_runner import AgentResult, RunContext

# The built-in tools the agent gets; everything else (web, sub-agents, MCP) is absent.
BUILTIN_TOOLS = ["Read", "Glob", "Grep", "Edit", "Write", "MultiEdit", "Bash"]
# Anchored (#244 S4): the URL must start the text after PULL_REQUEST and end at
# whitespace or the end, so ``/pull/12abc``, ``/pull/12/files`` and ``/pull/12?x`` are refused.
_PR_URL = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+(?=\s|$)")
_RESULT_LINE = re.compile(r"^RESULT:\s*(PULL_REQUEST|NO_CHANGE)\b[ \t]*(.*)$", re.MULTILINE)
_MAX_EXPLANATION = 500


def enforce(policy: ToolPolicy, log: ActionLog, fingerprint: str, tool_name: str,
            tool_input: dict[str, Any] | None) -> Decision:
    """Apply the policy; log a denial with allowlisted fields only (no input, no advisory text)."""
    decision = policy.check(tool_name, tool_input)
    if not decision.allowed:
        log.emit("tool_denied", outcome="denied", fingerprint=fingerprint, reason=decision.reason,
                 tool=tool_name if tool_name in KNOWN_TOOLS else "other")
    return decision


def parse_result(text: str | None, model: str, secrets: Sequence[str] = ()) -> AgentResult:
    """Read the agent's final ``RESULT:`` line. Anything unparseable is an error. A no-change
    explanation is redacted with ``secrets`` BEFORE it is cut to its window (#260 redact-first)."""
    matches = _RESULT_LINE.findall(text or "")
    if not matches:
        return AgentResult(outcome="error", model=model)
    kind, rest = matches[-1]
    if kind == "PULL_REQUEST":
        url = _PR_URL.match(rest.lstrip())
        if not url:
            return AgentResult(outcome="error", model=model)
        return AgentResult(outcome="pull_request_opened", model=model, pull_request=url.group(0))
    explanation = redacted_window("".join(c for c in rest if c.isprintable()), secrets, _MAX_EXPLANATION,
                                  tail=False).strip()
    return AgentResult(outcome="no_change", model=model, explanation=explanation or None)


def build_options(sdk: Any, *, model: str, system_prompt: str, ctx: RunContext,
                  api_key: str, github_token: str, environ: Mapping[str, str] | None = None) -> Any:
    """Build the SDK options for one run. Pure apart from reading the ``sdk`` classes."""
    if ctx.checkout is None or ctx.policy is None:
        raise RuntimeError("a live session needs a fresh checkout and a policy")
    policy, log, fp = ctx.policy, ctx.log, ctx.fingerprint

    async def can_use_tool(tool_name, tool_input, _context):
        decision = enforce(policy, log, fp, tool_name, tool_input)
        if decision.allowed:
            return sdk.PermissionResultAllow()
        return sdk.PermissionResultDeny(message=f"denied by responder policy: {decision.reason}")

    async def pre_tool_use(hook_input, _tool_use_id, _context):
        decision = enforce(policy, log, fp, hook_input.get("tool_name", ""), hook_input.get("tool_input"))
        if decision.allowed:
            return {}  # no opinion: the normal permission flow (can_use_tool) continues
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"denied by responder policy: {decision.reason}",
        }}

    # B1 (#244): the SDK starts the CLI with {**os.environ, **options.env}, so a responder
    # secret is kept out by overriding it with "". Everything not on the allowlist is
    # blanked first; the few names below are then set on purpose.
    env = {
        **blank_non_allowlisted(os.environ if environ is None else environ),
        "ANTHROPIC_API_KEY": api_key,
        # LIMIT: the agent runs `git push` and `gh pr create` itself through Bash, and every
        # Bash child inherits the CLI's environment, so these two cannot be hidden from the
        # code the agent runs. Bounded only by the token's scope (#222) and protect-main.
        "GH_TOKEN": github_token,
        MARKER_VAR: ctx.run_marker,  # lets the runner stop this run's processes (procs.py)
        # VERIFY: a commit needs an identity; the checkout has no git config of its own.
        "GIT_AUTHOR_NAME": "VulnTriage responder",
        "GIT_COMMITTER_NAME": "VulnTriage responder",
        "GIT_AUTHOR_EMAIL": "responder@users.noreply.github.com",
        "GIT_COMMITTER_EMAIL": "responder@users.noreply.github.com",
        **git_auth_env(github_token),
    }
    return sdk.ClaudeAgentOptions(
        tools=list(BUILTIN_TOOLS),
        system_prompt=system_prompt,
        model=model,
        max_turns=ctx.max_turns,
        max_budget_usd=ctx.max_budget_usd,  # VERIFY: the SDK passes it as --max-budget-usd (subprocess_cli.py)
        cwd=str(ctx.checkout),
        permission_mode="default",
        can_use_tool=can_use_tool,
        hooks={"PreToolUse": [sdk.HookMatcher(matcher=None, hooks=[pre_tool_use])]},
        setting_sources=[],  # SDK isolation: no user/project settings, hooks or CLAUDE.md
        env=env,
    )


class SdkSession:
    """One headless Agent SDK run for one alert."""

    def __init__(self, model: str, ctx: RunContext, *, api_key: str, github_token: str,
                 sdk: Any = None, secrets: Sequence[str] = ()) -> None:
        self._secrets = tuple(s for s in (api_key, github_token, *secrets) if s)
        self._model = model
        self._ctx = ctx
        self._api_key = api_key
        self._github_token = github_token
        self._sdk = sdk

    def run(self, system_prompt: str, task: str) -> AgentResult:
        sdk = self._sdk or importlib.import_module("claude_agent_sdk")  # lazy: the only SDK import
        return asyncio.run(asyncio.wait_for(self._converse(sdk, system_prompt, task),
                                            timeout=self._ctx.timeout_seconds))

    async def _converse(self, sdk: Any, system_prompt: str, task: str) -> AgentResult:
        options = build_options(sdk, model=self._model, system_prompt=system_prompt, ctx=self._ctx,
                                api_key=self._api_key, github_token=self._github_token)
        served: str | None = None
        final: Any = None
        async with sdk.ClaudeSDKClient(options=options) as client:
            await client.query(task)
            async for message in client.receive_response():
                if isinstance(message, sdk.AssistantMessage):
                    served = message.model or served
                elif isinstance(message, sdk.ResultMessage):
                    final = message
        model = served or self._model
        if final is None or final.is_error or final.subtype != "success":
            return AgentResult(outcome="error", model=model)  # includes error_max_turns
        return parse_result(final.result, model, self._secrets)
