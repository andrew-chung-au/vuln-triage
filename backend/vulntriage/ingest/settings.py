"""Ingestion settings, read from the process environment at call time."""

from __future__ import annotations

import os


def get_github_read_token() -> str | None:
    """The read-only GitHub token (``GITHUB_READ_TOKEN``), or None when unset or empty.

    The value is never logged, returned in an error or stored anywhere; it is
    sent only to ``api.github.com`` by :class:`vulntriage.ingest.github.GitHubReader`.
    """
    return os.environ.get("GITHUB_READ_TOKEN") or None
