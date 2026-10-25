"""Ingestion settings, read from the process environment at call time."""

from __future__ import annotations

import os


def get_github_read_token() -> str | None:
    """The read-only GitHub token (``GITHUB_READ_TOKEN``), or None when unset or empty.

    The value is never logged, returned in an error or stored anywhere; it is
    sent only to ``api.github.com`` by :class:`vulntriage.ingest.github.GitHubReader`.
    """
    return os.environ.get("GITHUB_READ_TOKEN") or None


# --- Feed source selection (VT_FEEDS) and the fail-closed environment gate ---
# task 40 (#172): a deployed/Compose scan must match/enrich/rank with no live
# feed. VT_FEEDS=live (default) uses real HTTP; VT_FEEDS=fixtures replays the
# committed fixtures. An unknown value stops start-up (never a silent fall-back
# to live). Fixture mode is refused unless DEPLOYMENT_ENVIRONMENT is explicitly
# dev or test, read RAW so unset/prod/unknown fail closed (A42; the same test
# VT_DEMO_DEFECT uses, A35; closes T-A8).

FEEDS_LIVE = "live"
FEEDS_FIXTURES = "fixtures"
_FEEDS_VALUES = (FEEDS_LIVE, FEEDS_FIXTURES)

# DEPLOYMENT_ENVIRONMENT values that permit fixture mode / the demo defect.
_NON_PRODUCTION_ENVIRONMENTS = ("dev", "test")


class FeedsConfigurationError(RuntimeError):
    """VT_FEEDS is an unknown value, or fixtures mode is used outside dev/test.

    Raised at start-up so a misconfiguration stops the backend rather than
    silently running against live feeds or shipping fixtures to production.
    """


def get_feeds_mode(environ: object = None) -> str:
    """Return the validated feed source: ``live`` (default) or ``fixtures``.

    Pure when ``environ`` is passed (a mapping): it reads only that mapping, so
    it is unit-testable. An unset value is ``live``; any value other than
    ``live``/``fixtures`` raises :class:`FeedsConfigurationError` (no silent
    fall-back). When fixtures is selected, the environment gate below must also
    pass; call :func:`require_feeds_allowed` at start-up to enforce it.
    """
    env = os.environ if environ is None else environ
    raw = env.get("VT_FEEDS")
    if not raw:
        return FEEDS_LIVE
    value = raw.strip()
    if value not in _FEEDS_VALUES:
        raise FeedsConfigurationError(
            f"VT_FEEDS={raw!r} is not valid; use one of {_FEEDS_VALUES} (or leave it unset for {FEEDS_LIVE!r})"
        )
    return value


def is_non_production_environment(environ: object = None) -> bool:
    """Whether DEPLOYMENT_ENVIRONMENT is EXPLICITLY ``dev`` or ``test``.

    Reads the RAW ``DEPLOYMENT_ENVIRONMENT`` value — NOT
    ``observability.settings.get_deployment_environment()``, which defaults to
    ``dev`` when unset and would fail open. Unset, ``prod``, or any other value
    returns False (treated as production), so the fixture-mode and demo-defect
    refusals fail closed. Pure when ``environ`` is passed.
    """
    env = os.environ if environ is None else environ
    raw = env.get("DEPLOYMENT_ENVIRONMENT")
    if raw is None:
        return False
    return raw.strip() in _NON_PRODUCTION_ENVIRONMENTS


def require_feeds_allowed(environ: object = None) -> str:
    """Validate VT_FEEDS and the environment gate at start-up; return the mode.

    Raises :class:`FeedsConfigurationError` when VT_FEEDS is unknown, or when
    fixtures mode is selected while the environment is not explicitly dev/test
    (fail closed: unset/prod/unknown refuse). Returns the validated mode so the
    caller can build the clients.
    """
    mode = get_feeds_mode(environ)
    if mode == FEEDS_FIXTURES and not is_non_production_environment(environ):
        env = os.environ if environ is None else environ
        shown = env.get("DEPLOYMENT_ENVIRONMENT")
        raise FeedsConfigurationError(
            "VT_FEEDS=fixtures is refused unless DEPLOYMENT_ENVIRONMENT is explicitly "
            f"'dev' or 'test' (got {shown!r}); fixtures must never run in production"
        )
    return mode


# --- Demo defect (VT_DEMO_DEFECT, task 28a / #218, A35) ---------------------
# The deliberate US-15 bug: with VT_DEMO_DEFECT=notify_no_fix the owner-
# notification formatter fails for a finding with no fixed version. Unset = off.
# An unknown value stops start-up (no silent ignore). The defect is refused
# unless DEPLOYMENT_ENVIRONMENT is explicitly dev/test, by the SAME fail-closed
# test as VT_FEEDS=fixtures (is_non_production_environment), so there is one
# gate, not two. Removed by the cleanup commit (#161, P-FLAG-GONE).

DEMO_DEFECT_NOTIFY_NO_FIX = "notify_no_fix"
_DEMO_DEFECT_VALUES = (DEMO_DEFECT_NOTIFY_NO_FIX,)


class DemoDefectConfigurationError(RuntimeError):
    """VT_DEMO_DEFECT is an unknown value, or is set outside dev/test.

    Raised at start-up so the demo defect can never run in production.
    """


def get_demo_defect(environ: object = None) -> str | None:
    """Return the validated demo defect name, or None when unset or empty.

    Pure when ``environ`` is passed. Any value other than ``notify_no_fix``
    raises :class:`DemoDefectConfigurationError` (no silent ignore).
    """
    env = os.environ if environ is None else environ
    raw = env.get("VT_DEMO_DEFECT")
    if not raw or not raw.strip():
        return None
    value = raw.strip()
    if value not in _DEMO_DEFECT_VALUES:
        raise DemoDefectConfigurationError(
            f"VT_DEMO_DEFECT={raw!r} is not valid; use one of {_DEMO_DEFECT_VALUES} (or leave it unset)"
        )
    return value


def require_demo_defect_allowed(environ: object = None) -> str | None:
    """Validate VT_DEMO_DEFECT and the environment gate at start-up.

    Raises :class:`DemoDefectConfigurationError` when the value is unknown, or
    when a defect is set while DEPLOYMENT_ENVIRONMENT is not explicitly dev/test
    (unset/prod/production/unknown refuse). Returns the defect name or None.
    """
    defect = get_demo_defect(environ)
    if defect is not None and not is_non_production_environment(environ):
        env = os.environ if environ is None else environ
        shown = env.get("DEPLOYMENT_ENVIRONMENT")
        raise DemoDefectConfigurationError(
            f"VT_DEMO_DEFECT={defect} is refused unless DEPLOYMENT_ENVIRONMENT is explicitly "
            f"'dev' or 'test' (got {shown!r}); the demo defect must never run in production"
        )
    return defect
