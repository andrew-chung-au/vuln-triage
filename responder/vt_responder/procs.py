"""Stop everything one agent run started (#244 S3).

The SDK starts the CLI without its own process group, so the runner cannot
``killpg`` it (that would be the responder's own group). Instead every process of
a run carries a marker in its environment (``VT_RUN_MARKER=<id>``, set in
``options.env``) and the agent's Bash children inherit it. ``kill_marked_processes``
finds them by reading ``/proc/<pid>/environ`` and sends SIGKILL.

Limits, stated plainly: Linux only (``/proc``); it needs the same user; a child
that deliberately starts with a cleaned environment (``env -i``) is not found.
It is a best-effort stop that closes the common leak, not a sandbox.
"""

from __future__ import annotations

import os
import signal
from pathlib import Path

MARKER_VAR = "VT_RUN_MARKER"


def kill_marked_processes(marker: str, *, proc_root: Path = Path("/proc")) -> int:
    """SIGKILL every process whose environment holds ``VT_RUN_MARKER=<marker>``. Returns how many."""
    if not marker:
        return 0
    needle = f"{MARKER_VAR}={marker}".encode()
    me = os.getpid()
    killed = 0
    try:
        entries = list(proc_root.iterdir())
    except OSError:
        return 0
    for entry in entries:
        if not entry.name.isdigit() or int(entry.name) == me:
            continue
        try:
            environ = (entry / "environ").read_bytes()
        except OSError:
            continue  # gone, or not ours
        if needle in environ.split(b"\0"):
            try:
                os.kill(int(entry.name), signal.SIGKILL)
                killed += 1
            except OSError:
                pass
    return killed
