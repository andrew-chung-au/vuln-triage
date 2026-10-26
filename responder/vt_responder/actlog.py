"""Action log: one structured JSON line per action.

Fields are an allowlist: ``event``, ``fingerprint``, ``finding_id``,
``outcome`` and a few short machine fields. Callers pass only those; there is
no free-form payload parameter, so tokens, secrets and advisory text have no
way in. ``explanation`` is text the responder itself wrote (what it checked),
never text read from the API.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, Callable, TextIO

_ALLOWED = frozenset(
    {
        "event",
        "fingerprint",
        "finding_id",
        "outcome",
        "explanation",
        "branch",
        "test_file",
        "fix_file",
        "pull_request",
        "job_states",
        "reason",
        "model",
        "tool",
    }
)


class ActionLog:
    def __init__(self, sink: TextIO | Callable[[str], Any] | None = None) -> None:
        self._sink = sink if sink is not None else sys.stdout

    def emit(self, event: str, *, outcome: str, fingerprint: str | None = None,
             finding_id: str | None = None, **extra: Any) -> dict[str, Any]:
        unknown = set(extra) - _ALLOWED
        if unknown:
            raise ValueError(f"fields not allowed in the action log: {sorted(unknown)}")
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": event,
            "fingerprint": fingerprint,
            "finding_id": finding_id,
            "outcome": outcome,
        }
        record.update(extra)
        line = json.dumps(record, sort_keys=True)
        if callable(self._sink):
            self._sink(line)
        else:
            self._sink.write(line + "\n")
            self._sink.flush()
        return record
