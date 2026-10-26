"""Repeat-fingerprint guard with a record that survives a restart.

The handled fingerprints are kept in a JSON file, rewritten atomically
(temp file, fsync, rename) on every change. ``claim`` is check-and-add under a
lock, so two concurrent deliveries of one fingerprint give one run.

Runs in flight are also written to a second small record (``<record>.inflight``),
because the handled record alone cannot tell "handled and finished" from "claimed
by a run that died with the process". On the next start every fingerprint still in
that record is released (``lost_on_restart``): a lost run is released, not stuck,
and the alert's next firing runs again. The deferred-resolve set and the failure
counts below stay in memory only (a restart clears them).
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path


class FingerprintGuard:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._inflight_path = self._path.with_name(self._path.name + ".inflight")
        self._lock = threading.Lock()
        self._handled = self._read_set(self._path, "handled-fingerprint record")
        # Runs in flight and resolved notifications waiting for them. The in-flight
        # set is mirrored to disk; the deferred set is memory only.
        self._inflight: set[str] = set()
        self._deferred: set[str] = set()
        # Consecutive failed runs per fingerprint (memory only; cleared by a success or a resolve).
        self._failures: dict[str, int] = {}
        # Runs the previous process never finished: released now so they are not stuck.
        lost = self._read_set(self._inflight_path, "in-flight record")
        self.lost_on_restart: list[str] = sorted(lost)
        if lost:
            self._handled -= lost
            self._write_set(self._path, self._handled)
        if lost or self._inflight_path.exists():
            self._write_set(self._inflight_path, set())

    @staticmethod
    def _read_set(path: Path, what: str) -> set[str]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return set()
        except (OSError, ValueError):
            # An unreadable record must not silently allow repeats: refuse to start.
            raise RuntimeError(f"cannot read {what} {path}") from None
        if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
            raise RuntimeError(f"{what} {path} is malformed")
        return set(data)

    @staticmethod
    def _write_set(path: Path, values: set[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(sorted(values), fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)

    def _save(self) -> None:
        self._write_set(self._path, self._handled)

    def _save_inflight(self) -> None:
        self._write_set(self._inflight_path, self._inflight)

    def claim(self, fingerprint: str) -> bool:
        """Return True the first time a fingerprint is seen, False after.

        A repeat firing that arrives while a release is deferred (see ``resolve``)
        cancels that release: the run in flight covers the alert that is firing now.
        """
        with self._lock:
            if fingerprint in self._handled:
                self._deferred.discard(fingerprint)
                return False
            # In-flight record first: a crash between the two writes must not leave a
            # handled fingerprint that no record says was running.
            self._inflight.add(fingerprint)
            self._save_inflight()
            self._handled.add(fingerprint)
            self._save()
            return True

    def failed_runs(self, fingerprint: str) -> int:
        """Consecutive failed runs recorded for this fingerprint since its last success or resolve."""
        with self._lock:
            return self._failures.get(fingerprint, 0)

    def abandon(self, fingerprint: str) -> None:
        """A claimed run never started (refused or cancelled while queued): release it, not a failure."""
        with self._lock:
            self._end_run_locked(fingerprint)
            self._release_locked(fingerprint)

    def release(self, fingerprint: str) -> None:
        """Forget a fingerprint (used when a run failed, so a re-sent alert retries)."""
        with self._lock:
            self._release_locked(fingerprint)

    def _release_locked(self, fingerprint: str) -> None:
        if fingerprint in self._handled:
            self._handled.discard(fingerprint)
            self._save()

    def resolve(self, fingerprint: str) -> str:
        """The alert resolved: forget the fingerprint so a later firing runs again.

        Returns ``released``, ``deferred`` (a run is in flight, so the release waits
        for ``finish``; releasing now would allow a second concurrent run) or
        ``unknown`` (nothing recorded; the record is left untouched).

        Limit: if a fix does not hold and the alert never resolves, Grafana sends
        nothing (no repeat), so the guard is not the cause.
        """
        with self._lock:
            self._failures.pop(fingerprint, None)  # a resolved alert lifts the retry cap
            if fingerprint in self._inflight:
                self._deferred.add(fingerprint)
                return "deferred"
            if fingerprint in self._handled:
                self._release_locked(fingerprint)
                return "released"
            return "unknown"

    def finish(self, fingerprint: str, *, failed: bool = False) -> None:
        """A run ended. Release it if it failed or a resolved was deferred (once)."""
        with self._lock:
            was_inflight = fingerprint in self._inflight
            deferred = fingerprint in self._deferred
            self._end_run_locked(fingerprint)
            if was_inflight:  # a stray second finish must not count twice
                if failed:
                    self._failures[fingerprint] = self._failures.get(fingerprint, 0) + 1
                else:
                    self._failures.pop(fingerprint, None)
            if failed or deferred:
                self._release_locked(fingerprint)

    def _end_run_locked(self, fingerprint: str) -> None:
        was_inflight = fingerprint in self._inflight
        self._inflight.discard(fingerprint)
        self._deferred.discard(fingerprint)
        if was_inflight:
            self._save_inflight()
