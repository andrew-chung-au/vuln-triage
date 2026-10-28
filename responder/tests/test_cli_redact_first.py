"""#260 redact-first: agent text is REDACTED IN FULL before it is cut to any window.

QA found that the CLI session cut the agent's text to an 800-character window (400 for a denied call)
before the exact-match redaction ran, so a secret bisected by the window edge survived as an unredacted
half, and with enough full copies of the secret in the window, redaction shrank the text so the
fragment fell inside the 500/300/200 characters that are kept. These tests put a secret (and its
base64 forms), repeated 1..30 times, across every window edge of every sink, with padding and
multi-byte text on both sides, and also pin the behaviours a mutation run showed were unguarded
(every occurrence redacted, the head of an escalation, the text of a limit error, characters not bytes).
"""

from __future__ import annotations

import json
import re

import pytest

from vt_responder.actlog import ActionLog
from vt_responder.cli_session import parse_output
from vt_responder.envscrub import redact, redacted_window, secret_forms
from vt_responder.publisher import compose_pull_request
from vt_responder.real_runner import RealRunner
from vt_responder.sdk_session import parse_result

from fake_claude import result_json
from test_cli_runtime import denial, run_failed_events, runner_rig
from test_real_runner_isolation import BRANCH, MODEL, events

pytestmark = pytest.mark.unit

SECRETS = {
    "github": "ghp_PLANTEDsecretvalue123",  # 25 characters
    "api": "vt-api-PLANTED-0123456789abcdef",  # 31
    "webhook": "whsec_PLANTED_0123456789",  # 24
    "ghlong": "github_pat_" + "AbCd1234" * 10,  # 91, the long fine-grained token shape
}
ALL = list(SECRETS.values())
PREFIXES = ("", "€€€", "\U0001F600\U0001F600\U0001F600")  # nothing, 3-byte and 4-byte characters
REPEATS = range(1, 31)


def leaked(text: str, secret: str, size: int = 8) -> bool:
    """True if ``size`` consecutive characters of the secret or of any of its base64 forms are in ``text``."""
    return any(form[i:i + size] in text for form in secret_forms(secret) for i in range(len(form) - size + 1))


def offsets(length: int, *, full: bool) -> list[int]:
    """Where in a secret form the window edge falls (1 = after its first character)."""
    if full:
        return list(range(1, length))
    return sorted({1, 2, 3, length // 4, length // 2, 3 * length // 4, length - 3, length - 2, length - 1})


# -- the sinks, in process: parse_output (the session) then the runner / publisher -----------------------

class Sinks:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.runner = RealRunner(None, ActionLog(self.lines.append), MODEL, None, secrets=ALL)  # type: ignore[arg-type]

    def failed(self, parsed):
        self.lines.clear()
        self.runner._error("fp1", "42", parsed.reason, explanation=parsed.explanation, denied_calls=parsed.denied_calls)
        return events(self.lines)[-1]

    def no_change(self, parsed):
        self.lines.clear()
        self.runner._no_change("fp1", "42", parsed.explanation or "x")
        return events(self.lines)[-1]["explanation"]


SINKS = Sinks()


def sink_tail(body: str, *, is_error: bool = False) -> tuple[str, int]:
    parsed = parse_output(result_json(body, is_error=is_error), MODEL, ALL)
    assert parsed.reason == ("agent_cli_error" if is_error else "result_line_missing")
    return SINKS.failed(parsed).get("explanation", ""), 500


def sink_escalate(rest: str) -> tuple[str, int]:
    parsed = parse_output(result_json("RESULT: ESCALATE " + rest), MODEL, ALL)
    assert parsed.reason == "agent_escalated"
    return SINKS.failed(parsed).get("explanation", ""), 500


def sink_no_change(rest: str) -> tuple[str, int]:
    parsed = parse_output(result_json("RESULT: FALSE_POSITIVE " + rest), MODEL, ALL)
    assert parsed.outcome == "no_change"
    return SINKS.no_change(parsed), 500


def sink_fixed(rest: str) -> tuple[str, int]:
    parsed = parse_output(result_json("RESULT: FIXED " + rest), MODEL, ALL)
    assert parsed.outcome == "fixed"
    return compose_pull_request("fp1", "42", ["backend/app.py"], parsed.explanation, ALL)[1], 10_000


def sink_denied(value: str) -> tuple[str, int]:
    parsed = parse_output(result_json("RESULT: ESCALATE x", permission_denials=[denial(value)]), MODEL, ALL)
    (entry,) = SINKS.failed(parsed)["denied_calls"]
    return entry, 200


def tail_body(form: str, k: int, j: int, prefix: str, gap: str, window: int = 800) -> str | None:
    """The last ``window`` characters begin ``j`` characters into the first of ``k`` copies of ``form``."""
    unit = form + gap
    filler = window + j - k * len(unit)
    return None if filler < 0 else prefix + "z" * 40 + unit * k + "q" * filler


def head_rest(form: str, k: int, j: int, prefix: str, gap: str, window: int = 800) -> str | None:
    """The first ``window`` characters end ``j`` characters into a copy of ``form``, after ``k`` whole copies."""
    unit = form + gap
    pad = window - j - k * len(unit) - len(prefix)
    return None if pad < 0 else prefix + unit * k + "q" * pad + form + " end " + "y" * 50


# (sink, builder, window of the session it targets); every sink is also checked for its cap
CASES = {
    "tail/result_line_missing": (sink_tail, tail_body, 800),
    "tail/agent_cli_error": (lambda b: sink_tail(b, is_error=True), tail_body, 800),
    "head/agent_escalated": (sink_escalate, head_rest, 800),
    "head/no_change": (sink_no_change, head_rest, 800),
    "head/fixed_to_pr_body_800": (sink_fixed, head_rest, 800),
    "head/fixed_to_pr_body_300": (sink_fixed, head_rest, 300),
    "head/denied_400": (sink_denied, head_rest, 400),
    "head/denied_runner_cut_194": (sink_denied, head_rest, 194),  # "Bash: " is 6 of the 200 kept
}


def sweep(case: str, secret_name: str, *, full_for: tuple[int, ...] = (1, 2, 3, 6, 15, 25, 30)) -> list:
    sink, build, window = CASES[case]
    failures = []
    secret = SECRETS[secret_name]
    for form in sorted(secret_forms(secret)):
        for k in REPEATS:
            for prefix in PREFIXES:
                for gap in (" ", "q"):
                    if prefix and gap == "q":
                        continue
                    for j in offsets(len(form), full=k in full_for and gap == " " and not prefix):
                        body = build(form, k, j, prefix, gap, window)
                        if body is None:
                            continue
                        text, cap = sink(body)
                        if leaked(text, secret) or len(text) > cap:
                            failures.append((len(form), k, j, prefix, gap, text[:60]))
    return failures


@pytest.mark.parametrize("secret_name", SECRETS)
@pytest.mark.parametrize("case", CASES)
def test_a_repeated_secret_across_a_window_edge_is_never_logged_even_in_part(case, secret_name):
    failures = sweep(case, secret_name)
    assert not failures, f"{len(failures)} leaking cases, first: {failures[:3]}"


@pytest.mark.parametrize("case", CASES)
def test_the_sweep_exercises_many_feasible_cases(case):
    """A guard against a sweep that skips everything: count the cases the builders accept."""
    sink, build, window = CASES[case]
    count = sum(build(f, k, j, "", " ", window) is not None
                for f in secret_forms(SECRETS["api"]) for k in REPEATS for j in (1, 10, 20))
    assert count >= 30


# -- the secret forms really appear in the bodies (the sweep is not vacuous) ------------------------------

def test_without_the_secrets_the_session_window_keeps_a_fragment():
    """The fragment is real: the same body, parsed with no secrets, leaves a bisected secret in the window."""
    form = SECRETS["ghp"] if "ghp" in SECRETS else SECRETS["github"]
    body = tail_body(form, 1, 12, "", " ")
    parsed = parse_output(result_json(body), MODEL, ())
    assert parsed.explanation and form[12:] in parsed.explanation


# -- the unit: redact first, then cut ---------------------------------------------------------------------

@pytest.mark.parametrize("name", SECRETS)
def test_redact_replaces_every_occurrence_of_every_form(name):
    secret = SECRETS[name]
    for form in secret_forms(secret):
        text = f"a {form} b {form} c {form}{form} d"
        out = redact(text, [secret])
        assert form not in out and out.count("[REDACTED]") == 4


def test_redacted_window_counts_the_size_on_the_redacted_text():
    secret = SECRETS["github"]
    text = "A" + secret + "B" + secret + "C"
    assert redacted_window(text, [secret], 100, tail=True) == "A[REDACTED]B[REDACTED]C"
    assert redacted_window(text, [secret], 100, tail=False) == "A[REDACTED]B[REDACTED]C"
    assert redacted_window(text, [secret], 12, tail=False) == "A[REDACTED]B"
    assert redacted_window(text, [secret], 12, tail=True) == "B[REDACTED]C"


def test_redacted_window_cuts_head_and_tail_by_characters_not_bytes():
    assert redacted_window("€" * 900, [], 500, tail=False) == "€" * 500
    assert redacted_window("€" * 900, [], 500, tail=True) == "€" * 500
    assert redacted_window("\U0001F600" * 900, ALL, 300, tail=False) == "\U0001F600" * 300


@pytest.mark.parametrize("name", SECRETS)
def test_the_whole_text_is_redacted_so_no_edge_of_any_region_can_bisect_a_secret(name):
    """Thousands of copies, the window far inside the text: every offset of every form, both ends."""
    secret = SECRETS[name]
    allowed = set("[REDACTED] q")  # the window may cut INSIDE a "[REDACTED]", which is harmless
    for form in sorted(secret_forms(secret)):
        unit = form + " "
        for lead in range(len(unit)):
            text = "q" * lead + unit * 3000
            for tail in (True, False):
                out = redacted_window(text, [secret], 800, tail=tail)
                assert len(out) == 800 and set(out) <= allowed and not leaked(out, secret)


def test_a_huge_final_message_is_redacted_near_its_end_and_bounded():
    secret = SECRETS["api"]
    body = "w" * 4_800_000 + " " + secret + " the end"
    parsed = parse_output(result_json(body), MODEL, ALL)
    assert parsed.reason == "result_line_missing" and len(parsed.explanation) <= 800
    assert parsed.explanation.endswith("[REDACTED] the end")
    rest = "q" * 4_800_000 + secret
    parsed = parse_output(result_json("RESULT: ESCALATE " + rest), MODEL, ALL)
    assert parsed.explanation == "q" * 800


# -- end to end through the fake `claude` executable ------------------------------------------------------

def run_logged(tmp_path, body, secret, *, is_error=False, exit=0, **extra):
    runner, lines, branches, *_ = runner_rig(
        tmp_path, stdout=result_json(body, is_error=is_error, **extra), secrets=(secret,) + tuple(ALL), exit=exit)
    outcome = runner.run("fp1", "42")
    return outcome, lines, branches


@pytest.mark.parametrize("name", SECRETS)
@pytest.mark.parametrize("kind", ["missing", "cli_error", "exit_nonzero", "escalate", "false_positive", "fixed",
                                  "denied"])
def test_end_to_end_a_repeated_bisected_secret_is_not_logged_or_published(tmp_path, name, kind):
    secret = SECRETS[name]
    form = secret
    k = max(1, min(6, 700 // (len(form) + 1)))
    if kind in ("missing", "cli_error", "exit_nonzero"):
        body = tail_body(form, k, len(form) // 2, "", " ")
        outcome, lines, _ = run_logged(tmp_path, body, secret, is_error=kind == "cli_error",
                                       exit=1 if kind == "exit_nonzero" else 0)
        want = {"missing": "result_line_missing", "cli_error": "agent_cli_error",
                "exit_nonzero": "cli_exit_nonzero"}[kind]
        (failed,) = run_failed_events(lines)
        assert failed["reason"] == want and failed.get("explanation")
        assert not leaked(json.dumps(failed), secret)
    elif kind == "escalate":
        outcome, lines, _ = run_logged(tmp_path, "RESULT: ESCALATE " + head_rest(form, k, len(form) // 2, "", " "), secret)
        (failed,) = run_failed_events(lines)
        assert failed["reason"] == "agent_escalated" and not leaked("\n".join(lines), secret)
    elif kind == "false_positive":
        outcome, lines, _ = run_logged(tmp_path, "RESULT: FALSE_POSITIVE " + head_rest(form, k, len(form) // 2, "", " "),
                                       secret)
        assert outcome == "no_change" and not leaked("\n".join(lines), secret)
    elif kind == "fixed":
        outcome, lines, branches = run_logged(tmp_path, "RESULT: FIXED " + head_rest(form, k, len(form) // 2, "", " "),
                                              secret)
        assert outcome == "pull_request_opened" and not leaked(branches.created[0]["body"], secret)
        assert not leaked("\n".join(lines), secret)
    else:
        value = head_rest(form, k, len(form) // 2, "", " ", 400)
        outcome, lines, _ = run_logged(tmp_path, "RESULT: ESCALATE no", secret, permission_denials=[denial(value)])
        (failed,) = run_failed_events(lines)
        assert failed["denied_calls"] and not leaked("\n".join(lines), secret)


def test_the_default_cli_session_is_built_with_every_configured_secret(tmp_path, monkeypatch):
    import vt_responder.real_runner as real_runner
    from conftest import make_settings
    from fake_claude import install
    from test_cli_runtime import make_ctx
    from vt_responder.app import create_app

    made: list = []

    class Capturing(real_runner.RealRunner):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            made.append(self)

    monkeypatch.setattr(real_runner, "RealRunner", Capturing)
    monkeypatch.setenv("PATH", str(install(tmp_path)))
    settings = make_settings(tmp_path, mode="real", model=MODEL, repo="o/r", github_token="gh-tok-value",
                             api_token="api-tok-value", webhook_secret="hook-secret-value", runtime="cli")
    create_app(settings)
    session = made[0]._make_session(MODEL, make_ctx(tmp_path))
    assert {"gh-tok-value", "api-tok-value", "hook-secret-value"} <= set(session._secrets)


def test_the_default_sdk_session_is_built_with_the_other_secrets(tmp_path, monkeypatch):
    import vt_responder.real_runner as real_runner
    from conftest import make_settings
    from test_cli_runtime import make_ctx
    from vt_responder.app import create_app

    seen: dict = {}
    monkeypatch.setattr(real_runner, "build_default_session", lambda model, ctx, **kw: seen.update(kw))
    settings = make_settings(tmp_path, mode="real", model=MODEL, repo="o/r", github_token="gh-tok-value",
                             api_token="api-tok-value", webhook_secret="hook-secret-value",
                             anthropic_api_key="key-value", runtime="sdk")
    captured: list = []

    class Capturing(real_runner.RealRunner):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            captured.append(self)

    monkeypatch.setattr(real_runner, "RealRunner", Capturing)
    create_app(settings)
    captured[0]._make_session(MODEL, make_ctx(tmp_path))
    assert {"api-tok-value", "hook-secret-value"} <= set(seen["secrets"])


# -- the SDK runtime's no-change explanation (cut to 500 before the runner redacts) ---------------------

@pytest.mark.parametrize("name", SECRETS)
def test_the_sdk_explanation_is_redacted_before_it_is_cut_to_500(name):
    secret = SECRETS[name]
    for form in sorted(secret_forms(secret)):
        for k in (1, 3, 8):
            for j in offsets(len(form), full=False):
                rest = head_rest(form, k, j, "", " ", 500)
                if rest is None:
                    continue
                parsed = parse_result("RESULT: NO_CHANGE " + rest, MODEL, [secret])
                assert not leaked(parsed.explanation or "", secret) and len(parsed.explanation) <= 500


# -- mutants the earlier suite did not catch ---------------------------------------------------------------

def test_an_escalation_logs_the_start_of_a_long_text_not_its_end(tmp_path):
    text = "HEAD-OF-TEXT " + "m" * 1200 + " TAIL-OF-TEXT"
    runner, lines, *_ = runner_rig(tmp_path, stdout=result_json("RESULT: ESCALATE " + text))
    runner.run("fp1", "42")
    (failed,) = run_failed_events(lines)
    assert failed["explanation"] == text[:500] and "TAIL-OF-TEXT" not in failed["explanation"]


def test_a_final_message_without_a_verdict_logs_the_end_of_a_long_text_not_its_start(tmp_path):
    text = "HEAD-OF-TEXT " + "m" * 1200 + " TAIL-OF-TEXT"
    runner, lines, *_ = runner_rig(tmp_path, stdout=result_json(text))
    runner.run("fp1", "42")
    (failed,) = run_failed_events(lines)
    assert failed["explanation"] == text[-500:] and "HEAD-OF-TEXT" not in failed["explanation"]


@pytest.mark.parametrize("fake,is_error", [({}, True), ({"exit": 1}, True), ({"exit": 1}, False)])
def test_the_text_of_a_plan_usage_limit_is_never_logged(tmp_path, fake, is_error):
    body = "You've hit your session limit. Resets 5pm. token ghp_PLANTEDsecretvalue123 SENTINEL-LIMIT-TEXT"
    runner, lines, *_ = runner_rig(tmp_path, stdout=result_json(body, is_error=is_error), **fake)
    runner.run("fp1", "42")
    (failed,) = run_failed_events(lines)
    assert failed["reason"] == "plan_usage_limit" and "explanation" not in failed
    assert "SENTINEL-LIMIT-TEXT" not in "\n".join(lines)


@pytest.mark.parametrize("fake", [{}, {"exit": 1}])
def test_the_text_of_a_turn_limit_run_is_never_logged(tmp_path, fake):
    out = result_json("SENTINEL-TURN-TEXT ghp_PLANTEDsecretvalue123", subtype="error_max_turns", is_error=True)
    runner, lines, *_ = runner_rig(tmp_path, stdout=out, **fake)
    runner.run("fp1", "42")
    (failed,) = run_failed_events(lines)
    assert failed["reason"] == "max_turns" and "explanation" not in failed
    assert "SENTINEL-TURN-TEXT" not in "\n".join(lines)


def test_a_usage_limit_message_wins_over_a_turn_limit_subtype():
    parsed = parse_output(result_json("You've hit your weekly limit", subtype="error_max_turns", is_error=True), MODEL)
    assert parsed.reason == "plan_usage_limit" and parsed.explanation is None


def test_the_session_windows_are_counted_in_characters_for_every_field():
    for body in ("RESULT: ESCALATE " + "€" * 900, "RESULT: FALSE_POSITIVE " + "€" * 900, "RESULT: FIXED " + "€" * 900,
                 "€" * 900):
        assert parse_output(result_json(body), MODEL, ALL).explanation == "€" * 800
    parsed = parse_output(result_json("RESULT: ESCALATE x", permission_denials=[denial("€" * 900)]), MODEL, ALL)
    assert parsed.denied_calls == ("Bash: " + "€" * 400,)


@pytest.mark.parametrize("kind", ["escalate", "tail", "no_change", "fixed", "denied"])
def test_the_logged_caps_are_counted_in_characters_for_every_sink(tmp_path, kind):
    euro = "€"
    out = {"escalate": result_json("RESULT: ESCALATE " + euro * 900), "tail": result_json(euro * 900),
           "no_change": result_json("RESULT: FALSE_POSITIVE " + euro * 900),
           "fixed": result_json("RESULT: FIXED " + euro * 900),
           "denied": result_json("RESULT: ESCALATE x", permission_denials=[denial(euro * 900)])}[kind]
    runner, lines, branches, *_ = runner_rig(tmp_path, stdout=out)
    runner.run("fp1", "42")
    if kind in ("escalate", "tail"):
        assert run_failed_events(lines)[0]["explanation"] == euro * 500
    elif kind == "no_change":
        assert [e for e in events(lines) if e["event"] == "no_change"][-1]["explanation"] == euro * 500
    elif kind == "fixed":
        assert euro * 300 in branches.created[0]["body"] and euro * 301 not in branches.created[0]["body"]
    else:
        assert run_failed_events(lines)[0]["denied_calls"] == ["Bash: " + euro * 194]


def test_the_branch_name_helper_is_importable():
    assert BRANCH == "responder/fp1"


@pytest.mark.parametrize("name", SECRETS)
def test_the_runner_alone_still_redacts_then_cuts_text_it_is_handed(name):
    """Defence in depth: whatever a session hands over, the runner redacts before it cuts."""
    secret = SECRETS[name]
    for pad in (480, 490, 495, 499, 500, 190, 194, 199):
        text = "x" * pad + secret + " tail"
        runner = SINKS.runner
        SINKS.lines.clear()
        runner._error("fp1", "42", "result_line_missing", explanation=text,
                      denied_calls=["Bash: " + text])
        failed = events(SINKS.lines)[-1]
        assert not leaked(json.dumps(failed), secret)
        SINKS.lines.clear()
        runner._error("fp1", "42", "agent_escalated", explanation=text)
        assert not leaked(json.dumps(events(SINKS.lines)[-1]), secret)
        SINKS.lines.clear()
        runner._no_change("fp1", "42", text)
        assert not leaked("\n".join(SINKS.lines), secret)


# -- an escalation or no-change verdict with no (or almost no) text still shows what the agent said ---------

PARAGRAPH = "I read the failing job and the retry code. " * 12  # about 500 characters


@pytest.mark.parametrize("verdict_text", ["", "   ", "\t \x1b\x00\x07", "\x1b[0m", "ok", "n/a"])
def test_an_escalation_with_empty_or_tiny_text_logs_the_tail_of_the_final_message(tmp_path, verdict_text):
    body = "START-MARK " + PARAGRAPH + " LAST-WORDS\nRESULT: ESCALATE " + verdict_text
    runner, lines, *_ = runner_rig(tmp_path, stdout=result_json(body))
    runner.run("fp1", "42")
    (failed,) = run_failed_events(lines)
    assert failed["reason"] == "agent_escalated"
    assert "LAST-WORDS" in failed["explanation"] and "RESULT: ESCALATE" in failed["explanation"]
    assert len(failed["explanation"]) <= 500 and "START-MARK" not in failed["explanation"]


def test_an_escalation_with_a_real_explanation_still_logs_only_that_explanation(tmp_path):
    body = PARAGRAPH + "\nRESULT: ESCALATE the fix needs a schema migration, which I may not run"
    runner, lines, *_ = runner_rig(tmp_path, stdout=result_json(body))
    runner.run("fp1", "42")
    assert run_failed_events(lines)[0]["explanation"] == "the fix needs a schema migration, which I may not run"


@pytest.mark.parametrize("verdict_text", ["", " \x1b "])
def test_a_false_positive_with_no_text_logs_the_tail_of_the_final_message(tmp_path, verdict_text):
    body = PARAGRAPH + " LAST-WORDS\nRESULT: FALSE_POSITIVE " + verdict_text
    runner, lines, *_ = runner_rig(tmp_path, stdout=result_json(body))
    assert runner.run("fp1", "42") == "no_change"
    text = [e for e in events(lines) if e["event"] == "no_change"][-1]["explanation"]
    assert "LAST-WORDS" in text and len(text) <= 500


def test_a_fixed_verdict_with_no_text_adds_no_agent_summary_to_the_pull_request(tmp_path):
    runner, lines, branches, *_ = runner_rig(tmp_path, stdout=result_json(PARAGRAPH + "\nRESULT: FIXED"))
    assert runner.run("fp1", "42") == "pull_request_opened"
    assert "Agent summary" not in branches.created[0]["body"]


@pytest.mark.parametrize("name", SECRETS)
def test_the_fallback_tail_is_redacted_before_it_is_cut(name):
    secret = SECRETS[name]
    for form in sorted(secret_forms(secret)):
        for k in (1, 4, 10):
            for j in offsets(len(form), full=False):
                body = tail_body(form, k, j, "", " ", 500)
                if body is None:
                    continue
                for verdict in ("RESULT: ESCALATE", "RESULT: FALSE_POSITIVE  "):
                    parsed = parse_output(result_json(body + "\n" + verdict), MODEL, ALL)
                    logged = SINKS.failed(parsed).get("explanation", "") if parsed.reason else \
                        SINKS.no_change(parsed)
                    assert not leaked(logged, secret) and 0 < len(logged) <= 500


def test_a_verdict_inside_a_code_fence_is_not_a_verdict_and_its_tail_is_logged(tmp_path):
    body = "I ran the script:\n```\nRESULT: ESCALATE quoted from a log\n```\nthen I stopped. FINAL-WORDS"
    runner, lines, *_ = runner_rig(tmp_path, stdout=result_json(body))
    runner.run("fp1", "42")
    (failed,) = run_failed_events(lines)
    assert failed["reason"] == "result_line_missing" and failed["explanation"].endswith("FINAL-WORDS")


def test_text_after_the_verdict_line_does_not_replace_its_explanation(tmp_path):
    body = "RESULT: ESCALATE needs a human to approve the migration\nsome trailing remarks " + "t" * 900
    runner, lines, *_ = runner_rig(tmp_path, stdout=result_json(body))
    runner.run("fp1", "42")
    assert run_failed_events(lines)[0]["explanation"] == "needs a human to approve the migration"


def test_a_short_escalation_text_with_trailing_remarks_logs_the_tail_too(tmp_path):
    body = "RESULT: ESCALATE hmm\nbut here is why: " + "w" * 100 + " WHY-END"
    runner, lines, *_ = runner_rig(tmp_path, stdout=result_json(body))
    runner.run("fp1", "42")
    assert "WHY-END" in run_failed_events(lines)[0]["explanation"]
