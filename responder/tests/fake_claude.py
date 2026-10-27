"""A fake ``claude`` executable for the CLI-runtime tests (#260). No login, no network, no model call.

``install(tmp_path, ...)`` writes an executable script into a fresh directory and returns that
directory; a test puts it on the ``PATH`` it hands to the code under test. The script answers
``--version``, ``--help`` and ``auth status`` like the real CLI is documented to, and for a ``-p`` run
it records its argv, environment, working directory, process-group id and stdin to a JSON-lines log,
then prints the scripted output and exits with the scripted code (optionally after sleeping and
starting a child process, to exercise the time limit and the process-group kill).
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

from vt_responder.cli_session import REQUIRED_HELP_FLAGS

SCRIPT = """#!@PYTHON@
import json, os, subprocess, sys, time

here = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(os.path.join(here, "config.json")))


def log(entry):
    with open(cfg["log"], "a") as handle:
        handle.write(json.dumps(entry) + "\\n")


args = sys.argv[1:]
if args == ["--version"]:
    print("2.1.311 (Claude Code)")
    sys.exit(0)
if args == ["--help"]:
    log({"kind": "help", "env": dict(os.environ)})
    shown = [f for f in cfg["help_flags"] if f not in cfg["help_missing"]]
    print("Usage: claude [options]\\n" + "\\n".join("  " + f for f in shown))
    sys.exit(0)
if args[:2] == ["auth", "status"]:
    log({"kind": "status", "env": dict(os.environ)})
    status = cfg["status"]
    if status["exit"] != 0:
        print(json.dumps({"loggedIn": False, "authMethod": "none"}))
        sys.exit(status["exit"])
    print(json.dumps({"loggedIn": True, "authMethod": status["method"]}))
    sys.exit(0)

stdin = sys.stdin.read()
entry = {"kind": "run", "argv": args, "env": dict(os.environ), "cwd": os.getcwd(), "stdin": stdin,
         "pid": os.getpid(), "pgid": os.getpgrp()}
run = cfg["run"]
if run["spawn_child"]:
    child = subprocess.Popen(["sleep", "60"])
    entry["child_pid"] = child.pid
log(entry)
if run["sleep"]:
    time.sleep(run["sleep"])
sys.stdout.write(run["stdout"])
sys.stderr.write(run["stderr"])
sys.exit(run["exit"])
"""


def result_json(text: str, **over: Any) -> str:
    """What ``claude -p --output-format json`` is documented to print for a finished run."""
    data = {"type": "result", "subtype": "success", "is_error": False, "result": text, "num_turns": 4,
            "session_id": "00000000-0000-0000-0000-000000000000", "modelUsage": {"claude-sonnet-5-5": {}}}
    data.update(over)
    return json.dumps(data)


def install(tmp_path: Path, *, stdout: str = "", stderr: str = "", exit: int = 0, sleep: float = 0.0,
            spawn_child: bool = False, login_exit: int = 0, method: str = "claude.ai",
            help_missing: tuple[str, ...] = ()) -> Path:
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    (bin_dir / "config.json").write_text(json.dumps({
        "log": str(tmp_path / "claude-calls.jsonl"),
        "help_flags": list(REQUIRED_HELP_FLAGS), "help_missing": list(help_missing),
        "status": {"exit": login_exit, "method": method},
        "run": {"stdout": stdout, "stderr": stderr, "exit": exit, "sleep": sleep, "spawn_child": spawn_child},
    }))
    script = bin_dir / "claude"
    script.write_text(SCRIPT.replace("@PYTHON@", sys.executable))
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return bin_dir


def calls(tmp_path: Path, kind: str | None = None) -> list[dict[str, Any]]:
    log = tmp_path / "claude-calls.jsonl"
    if not log.exists():
        return []
    entries = [json.loads(line) for line in log.read_text().splitlines()]
    return [e for e in entries if kind is None or e["kind"] == kind]


def is_dead(pid: int) -> bool:
    """True if ``pid`` is gone or a zombie (a killed orphan may wait for a reaper)."""
    try:
        stat_line = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return True
    return stat_line.rsplit(")", 1)[1].split()[0] == "Z"


def host_env(bin_dir: Path, **extra: str) -> dict[str, str]:
    """A responder-like environment holding every secret the CLI must NOT see, plus the PATH and
    HOME it needs. The fake ``claude`` is found through ``PATH``."""
    return {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', os.defpath)}", "HOME": "/home/owner",
        "ANTHROPIC_API_KEY": "PLANTED-ANTHROPIC-API-KEY", "ANTHROPIC_AUTH_TOKEN": "PLANTED-ANTHROPIC-AUTH-TOKEN",
        "RESPONDER_GITHUB_TOKEN": "PLANTED-RESPONDER-GITHUB-TOKEN", "GH_TOKEN": "PLANTED-GH-TOKEN",
        "RESPONDER_API_TOKEN": "PLANTED-RESPONDER-API-TOKEN", "RESPONDER_WEBHOOK_SECRET": "PLANTED-WEBHOOK",
        "GIT_CONFIG_VALUE_0": "PLANTED-GIT-CONFIG", "AWS_SECRET_ACCESS_KEY": "PLANTED-AWS",
        **extra,
    }
