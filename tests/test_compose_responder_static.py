"""Static, offline checks of ``compose.responder.yaml`` and the ``responder`` job script (#220).

These run in ``make test`` / ``make verify`` (no Docker). The container cases that
use the file are in ``tests/test_compose_responder.py`` and run only under
``make test-compose JOB=responder``.

PyYAML is not in the backend environment (and a new dependency needs approval), so
the compose file is read with a small indentation-based text parser. It is enough
for this file's shape (block mappings and ``- item`` lists); the parser's own
limits are covered by the bad-input cases below.
"""

from __future__ import annotations

import os
import pathlib
import re
import stat
import subprocess

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_COMPOSE = _ROOT / "compose.responder.yaml"
_SCRIPT = _ROOT / "ci" / "test-compose.sh"

_FORBIDDEN_KEY_PREFIXES = ("GITHUB_", "GH_", "ANTHROPIC_", "AWS_")


def _strip(text: str) -> list[tuple[int, str]]:
    """(indent, content) for each non-blank, non-comment line."""
    out = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        out.append((len(raw) - len(raw.lstrip(" ")), raw.strip()))
    return out


def _service_block(text: str, name: str) -> list[tuple[int, str]]:
    """The lines (with indent) under ``services: <name>:``, excluding the header."""
    lines = _strip(text)
    in_services = False
    block: list[tuple[int, str]] = []
    collecting = False
    for indent, content in lines:
        if indent == 0:
            in_services = content == "services:"
            collecting = False
            continue
        if not in_services:
            continue
        if indent == 2:
            collecting = content == f"{name}:"
            continue
        if collecting:
            block.append((indent, content))
    return block


def _child_keys(block: list[tuple[int, str]], parent: str) -> list[str]:
    """Keys of the mapping directly under ``parent:`` (one level deeper)."""
    keys: list[str] = []
    parent_indent: int | None = None
    for indent, content in block:
        if parent_indent is None:
            if content == f"{parent}:":
                parent_indent = indent
            continue
        if indent <= parent_indent:
            break
        if indent == parent_indent + 2 and not content.startswith("- "):
            keys.append(content.split(":", 1)[0].strip())
    return keys


def _list_items(block: list[tuple[int, str]], parent: str) -> list[str]:
    items: list[str] = []
    parent_indent: int | None = None
    for indent, content in block:
        if parent_indent is None:
            if content == f"{parent}:":
                parent_indent = indent
            continue
        if indent <= parent_indent:
            break
        if content.startswith("- "):
            items.append(content[2:].strip().strip('"').strip("'"))
    return items


def _top_keys(block: list[tuple[int, str]]) -> set[str]:
    if not block:
        return set()
    base = min(i for i, _ in block)
    return {c.split(":", 1)[0] for i, c in block if i == base and not c.startswith("- ")}


def responder_problems(text: str) -> list[str]:
    """Everything wrong with the ``responder`` service in a compose file's text."""
    block = _service_block(text, "responder")
    if not block:
        return ["no responder service"]
    problems: list[str] = []
    top = _top_keys(block)
    if "env_file" in top:
        problems.append("responder has an env_file")
    if "image" in top:
        problems.append("responder names an image (it must be built from ./backend)")
    if "build" not in top:
        problems.append("responder has no build")
    elif "context: ./backend" not in {c for _, c in block}:
        problems.append("responder is not built from ./backend")
    env_keys = _child_keys(block, "environment")
    if not env_keys:
        problems.append("responder has no environment")
    for key in env_keys:
        if "TOKEN" in key and key != "RESPONDER_API_TOKEN":
            problems.append(f"responder env key {key} contains TOKEN")
        if key.startswith(_FORBIDDEN_KEY_PREFIXES):
            problems.append(f"responder env key {key} is forbidden")
    if "PYTHONPATH" not in env_keys:
        problems.append("responder sets no PYTHONPATH")
    state = [c for _, c in block if c.startswith("RESPONDER_STATE_FILE:")]
    if not state or not state[0].split(":", 1)[1].strip().startswith("/tmp/"):
        problems.append("responder guard state file is not under /tmp/")
    if "./responder/vt_responder:/responder/vt_responder:ro" not in _list_items(block, "volumes"):
        problems.append("responder does not bind-mount ./responder/vt_responder read-only")
    ports = _list_items(block, "ports")
    if not ports:
        problems.append("responder publishes no port")
    for port in ports:
        if not port.startswith("127.0.0.1:"):
            problems.append(f"responder port {port!r} is not published on 127.0.0.1")
    return problems


def test_responder_service_is_built_from_backend_and_holds_no_secrets() -> None:
    assert responder_problems(_COMPOSE.read_text(encoding="utf-8")) == []


def test_responder_uses_the_shared_webhook_token_and_fails_closed_by_default() -> None:
    block = _service_block(_COMPOSE.read_text(encoding="utf-8"), "responder")
    lines = {c for _, c in block}
    assert "RESPONDER_WEBHOOK_SECRET: ${VT_RESPONDER_WEBHOOK_TOKEN:?set VT_RESPONDER_WEBHOOK_TOKEN}" in lines
    # Mode and API token default to empty, which the responder refuses at startup.
    assert "RESPONDER_MODE: ${RESPONDER_MODE:-}" in lines
    assert "RESPONDER_API_TOKEN: ${RESPONDER_API_TOKEN:-}" in lines


def test_backend_passes_the_demo_defect_through() -> None:
    block = _service_block(_COMPOSE.read_text(encoding="utf-8"), "backend")
    assert "VT_DEMO_DEFECT: ${VT_DEMO_DEFECT:-}" in {c for _, c in block}


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("    env_file: .env\n", "env_file"),
        ("      ANTHROPIC_API_KEY: x\n", "ANTHROPIC_API_KEY"),
        ("      GITHUB_READ_TOKEN: x\n", "GITHUB_READ_TOKEN"),
        ("      AWS_ACCESS_KEY_ID: x\n", "AWS_ACCESS_KEY_ID"),
        ("      SOME_OTHER_TOKEN: x\n", "SOME_OTHER_TOKEN"),
    ],
)
def test_checker_refuses_secrets_in_the_responder_service(mutation: str, expected: str) -> None:
    text = _COMPOSE.read_text(encoding="utf-8")
    bad = text.replace("    working_dir: /app\n", "    working_dir: /app\n" + mutation, 1)
    if mutation.startswith("      "):
        bad = text.replace("      PYTHONPATH: /responder\n", "      PYTHONPATH: /responder\n" + mutation, 1)
    assert bad != text
    assert any(expected in p for p in responder_problems(bad)), responder_problems(bad)


@pytest.mark.parametrize("port", ["9100:9100", "0.0.0.0:9100:9100", "9100"])
def test_checker_refuses_a_port_not_on_loopback(port: str) -> None:
    text = _COMPOSE.read_text(encoding="utf-8")
    bad = text.replace('"127.0.0.1:9100:9100"', f'"{port}"')
    assert bad != text
    assert any("127.0.0.1" in p for p in responder_problems(bad))


def test_checker_refuses_a_state_file_outside_tmp() -> None:
    text = _COMPOSE.read_text(encoding="utf-8")
    bad = text.replace("/tmp/responder-state", "/var/lib/responder-state")
    assert any("/tmp/" in p for p in responder_problems(bad))


def test_checker_refuses_a_missing_service() -> None:
    assert responder_problems("services:\n  other:\n    image: x\n") == ["no responder service"]


# -- ci/test-compose.sh: the responder branch is implemented ------------------


def test_script_is_valid_bash() -> None:
    result = subprocess.run(["bash", "-n", str(_SCRIPT)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_script_responder_branch_is_wired_and_all_jobs_run_without_the_stub() -> None:
    text = _SCRIPT.read_text(encoding="utf-8")
    assert re.search(r"^\s*responder\)\s+run_responder\s*;;", text, re.MULTILINE)
    assert "run_not_implemented" not in text
    assert "not implemented" not in text.lower()
    # The no-JOB path runs all three jobs.
    for call in ("run_telemetry || rc=$?", "run_alert || rc=$?", "run_responder || rc=$?"):
        assert call in text


def test_script_exports_the_throwaway_values_the_responder_job_needs() -> None:
    text = _SCRIPT.read_text(encoding="utf-8")
    start = text.index("run_responder() {")
    body = text[start:]
    assert 'PROJECT="vt-responder"' in body
    assert 'export RESPONDER_MODE="stub"' in body
    assert 'export VT_RESPONDER_WEBHOOK_URL="http://responder:9100/webhook/grafana"' in body
    # A non-empty shared API token (compose.yaml defaults it to empty).
    assert re.search(r'export RESPONDER_API_TOKEN="\$\{RESPONDER_API_TOKEN:-[^}]+\}"', body)


def test_job_responder_no_longer_exits_3(tmp_path: pathlib.Path) -> None:
    """With a fake ``docker`` that always fails, JOB=responder fails at ``up`` (exit 1), not 3.

    The fake docker is the only thing on PATH that matters: the script checks
    ``command -v docker``, then the responder branch runs ``docker compose ... up``,
    which fails, so the branch returns 1 and the cleanup trap calls the fake again.
    Exit 3 and the "not implemented" text belonged to the old stub.
    """
    fake = tmp_path / "docker"
    fake.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    env = dict(os.environ, JOB="responder", PATH=f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    if not (_ROOT / "backend" / ".venv" / "bin" / "pytest").exists():
        pytest.fail("backend/.venv is missing: run make install first")
    result = subprocess.run(
        ["bash", str(_SCRIPT)], capture_output=True, text=True, env=env, cwd=_ROOT, timeout=60, check=False
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "not implemented" not in (result.stdout + result.stderr).lower()
