"""#221 SdkSession and build_default_session against a FAKE SDK (no key, no network).

One test builds the real ``ClaudeAgentOptions`` (no connection is made) to catch a
misspelt option name. Nothing here starts the Claude Code process.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from vt_responder.actlog import ActionLog
from vt_responder.config import ConfigError
from vt_responder.policy import ToolPolicy
from vt_responder.real_runner import AgentResult, RunContext, build_default_session
from vt_responder.sdk_session import SdkSession, build_options, parse_result

pytestmark = pytest.mark.unit

MODEL = "claude-sonnet-5-5"
KEY, TOKEN = "PLANTED-ANTHROPIC-KEY", "PLANTED-GH-TOKEN"
PR = "https://github.com/o/r/pull/12"


# -- a fake SDK module -------------------------------------------------------

@dataclass
class Opts:
    kwargs: dict[str, Any] = field(default_factory=dict)

    def __init__(self, **kwargs): self.kwargs = kwargs


@dataclass
class Matcher:
    matcher: Any = None
    hooks: list = field(default_factory=list)


@dataclass
class Allow:
    behavior: str = "allow"


@dataclass
class Deny:
    message: str = ""
    behavior: str = "deny"


@dataclass
class Assistant:
    model: str


@dataclass
class Result:
    is_error: bool = False
    subtype: str = "success"
    result: str | None = None


class FakeSdk:
    ClaudeAgentOptions = Opts
    HookMatcher = Matcher
    PermissionResultAllow = Allow
    PermissionResultDeny = Deny
    AssistantMessage = Assistant
    ResultMessage = Result

    def __init__(self, messages, *, delay: float = 0.0) -> None:
        sdk = self
        self.queries: list[str] = []
        self.options: list[Opts] = []

        class Client:
            def __init__(self, options): sdk.options.append(options)
            async def __aenter__(self): return self
            async def __aexit__(self, *exc): return False
            async def query(self, prompt): sdk.queries.append(prompt)
            async def receive_response(self):
                await asyncio.sleep(delay)
                for m in messages:
                    yield m

        self.ClaudeSDKClient = Client


def make_ctx(tmp_path: Path, lines: list[str] | None = None, **over) -> RunContext:
    root = tmp_path / "checkout"
    (root / "backend").mkdir(parents=True, exist_ok=True)
    (root / ".github").mkdir(exist_ok=True)
    lines = [] if lines is None else lines
    base = dict(fingerprint="fp1", checkout=root, policy=ToolPolicy(root, "fp1"),
                log=ActionLog(lines.append), max_turns=9, timeout_seconds=5)
    base.update(over)
    return RunContext(**base)


def session(tmp_path, sdk, **over):
    return SdkSession(MODEL, make_ctx(tmp_path, **over), api_key=KEY, github_token=TOKEN, sdk=sdk)


# -- outcomes ---------------------------------------------------------------

def test_pull_request_result_reports_the_api_served_model(tmp_path):
    sdk = FakeSdk([Assistant("claude-sonnet-5-5-served"), Result(result=f"Done.\nRESULT: PULL_REQUEST {PR}")])
    out = session(tmp_path, sdk).run("SYS", "do the task")
    assert out == AgentResult("pull_request_opened", "claude-sonnet-5-5-served", pull_request=PR)
    assert sdk.queries == ["do the task"]


def test_no_change_result_carries_a_bounded_explanation(tmp_path):
    long = "x" * 2000
    sdk = FakeSdk([Assistant(MODEL), Result(result=f"RESULT: NO_CHANGE {long}")])
    out = session(tmp_path, sdk).run("SYS", "t")
    assert out.outcome == "no_change" and len(out.explanation) == 500


@pytest.mark.parametrize("final", [
    Result(is_error=True), Result(subtype="error_max_turns"), Result(result="I fixed it, trust me."),
    Result(result="RESULT: PULL_REQUEST not-a-url"), Result(result="RESULT: PULL_REQUEST https://evil.example/pull/1"),
    Result(result=None),
])
def test_error_and_unparseable_results_are_errors(tmp_path, final):
    out = session(tmp_path, FakeSdk([Assistant(MODEL), final])).run("SYS", "t")
    assert out.outcome == "error"


def test_no_result_message_is_an_error(tmp_path):
    assert session(tmp_path, FakeSdk([Assistant(MODEL)])).run("SYS", "t").outcome == "error"


def test_the_time_limit_stops_the_session(tmp_path):
    sdk = FakeSdk([Assistant(MODEL), Result(result=f"RESULT: PULL_REQUEST {PR}")], delay=2.0)
    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        session(tmp_path, sdk, timeout_seconds=0.1).run("SYS", "t")


def test_parse_result_takes_the_last_result_line():
    text = f"RESULT: NO_CHANGE early\nthen more\nRESULT: PULL_REQUEST {PR}"
    assert parse_result(text, MODEL).outcome == "pull_request_opened"


# -- options: model, turns, cwd, allowlist wiring ----------------------------

def test_options_use_the_configured_model_turns_checkout_and_isolation(tmp_path):
    sdk = FakeSdk([Assistant(MODEL), Result(result="RESULT: NO_CHANGE ok")])
    ctx = make_ctx(tmp_path)
    SdkSession(MODEL, ctx, api_key=KEY, github_token=TOKEN, sdk=sdk).run("SYS PROMPT", "t")
    o = sdk.options[0].kwargs
    assert o["model"] == MODEL and o["max_turns"] == 9 and o["cwd"] == str(ctx.checkout)
    assert o["system_prompt"] == "SYS PROMPT"
    assert o["setting_sources"] == []  # no user/project settings or hooks from the checkout
    assert o["permission_mode"] == "default" and "allowed_tools" not in o  # nothing pre-approved
    assert "WebFetch" not in o["tools"] and "Task" not in o["tools"]
    assert o["env"]["ANTHROPIC_API_KEY"] == KEY and o["env"]["GH_TOKEN"] == TOKEN


def test_callback_and_hook_apply_the_policy_and_log_denials(tmp_path):
    lines: list[str] = []
    ctx = make_ctx(tmp_path, lines)
    sdk = FakeSdk([])
    opts = build_options(sdk, model=MODEL, system_prompt="s", ctx=ctx, api_key=KEY, github_token=TOKEN).kwargs
    can_use = opts["can_use_tool"]
    hook = opts["hooks"]["PreToolUse"][0].hooks[0]

    assert asyncio.run(can_use("Edit", {"file_path": "backend/a.py"}, None)) == Allow()
    denied = asyncio.run(can_use("Edit", {"file_path": ".github/workflows/x.yml"}, None))
    assert isinstance(denied, Deny) and "github_dir" in denied.message

    assert asyncio.run(hook({"tool_name": "Read", "tool_input": {"file_path": "backend/a.py"}}, "id", {})) == {}
    out = asyncio.run(hook({"tool_name": "Read", "tool_input": {"file_path": ".env"}}, "id", {}))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    out = asyncio.run(hook({"tool_name": "Bash", "tool_input": {"command": "git push origin main"}}, "id", {}))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    reasons = [json.loads(x)["reason"] for x in lines]
    assert reasons == ["github_dir", "env_file", "push_main"]
    assert all(json.loads(x)["event"] == "tool_denied" for x in lines)


def test_a_session_without_a_checkout_is_refused(tmp_path):
    ctx = make_ctx(tmp_path, checkout=None, policy=None)
    with pytest.raises(RuntimeError):
        build_options(FakeSdk([]), model=MODEL, system_prompt="s", ctx=ctx, api_key=KEY, github_token=TOKEN)


def test_options_build_with_the_real_sdk_classes_without_connecting(tmp_path):
    # Catches a misspelt option name or hook shape against the pinned SDK. No process is started.
    sdk = pytest.importorskip("claude_agent_sdk")
    opts = build_options(sdk, model=MODEL, system_prompt="s", ctx=make_ctx(tmp_path), api_key=KEY, github_token=TOKEN)
    assert opts.model == MODEL and opts.max_turns == 9 and opts.setting_sources == []
    assert callable(opts.can_use_tool) and "PreToolUse" in opts.hooks


# -- build_default_session: refusals at the live boundary --------------------

def test_default_session_is_refused_in_test_and_ci(tmp_path):
    ctx = make_ctx(tmp_path)
    for env in ({"CI": "true"}, {"GITHUB_ACTIONS": "true"}, {"PYTEST_CURRENT_TEST": "x"},
                {"DEPLOYMENT_ENVIRONMENT": "test"}):
        with pytest.raises(ConfigError, match="test and CI"):
            build_default_session(MODEL, ctx, api_key=KEY, github_token=TOKEN, env=env, sdk=FakeSdk([]))


def test_default_session_is_refused_without_key_or_token(tmp_path):
    ctx = make_ctx(tmp_path)
    for key, token in (("", TOKEN), (KEY, ""), ("", "")):
        with pytest.raises(ConfigError) as err:
            build_default_session(MODEL, ctx, api_key=key, github_token=token, env={}, sdk=FakeSdk([]))
        assert KEY not in str(err.value) and TOKEN not in str(err.value)


def test_default_session_is_built_outside_test_and_ci_and_runs_the_fake_sdk(tmp_path):
    sdk = FakeSdk([Assistant(MODEL), Result(result="RESULT: NO_CHANGE fine")])
    s = build_default_session(MODEL, make_ctx(tmp_path), api_key=KEY, github_token=TOKEN, env={}, sdk=sdk)
    assert s.run("SYS", "t").outcome == "no_change"


def test_secrets_never_reach_the_log(tmp_path):
    lines: list[str] = []
    ctx = make_ctx(tmp_path, lines)
    opts = build_options(FakeSdk([]), model=MODEL, system_prompt="s", ctx=ctx, api_key=KEY, github_token=TOKEN).kwargs
    asyncio.run(opts["can_use_tool"]("Bash", {"command": f"cat .env {KEY}"}, None))
    assert KEY not in "\n".join(lines) and TOKEN not in "\n".join(lines)
