"""Guard: the `compose` marker may only appear in known compose test modules.

The gate (``_docs/agent-kit/procedures/verify.md``) catches a newly added
``skip``/``xfail`` marker, but it does NOT catch an ordinary backend test being
newly tagged ``compose`` — which would silently remove it from ``make test``
(``backend-test`` runs ``-m "not compose"``). This unit test closes that gap: it
scans every test module and fails if ``pytest.mark.compose`` (or a
``pytestmark = pytest.mark.compose``) appears in any file other than the
explicitly allowed compose modules.

The allowlist is an explicit set, not a glob, so a file cannot exempt itself
merely by being named ``test_compose_*.py`` (adding a new compose module is a
deliberate edit here, which is the point — it keeps the drop-from-``make test``
decision visible in review).

It is a plain ``unit`` case, so it runs in ``make test`` / ``make verify`` and
needs no Docker.
"""

from __future__ import annotations

import pathlib
import re

import pytest

pytestmark = pytest.mark.unit

# The only modules allowed to carry the `compose` marker. Adding one is a
# deliberate change reviewed here (it drops that module from `make test`).
_ALLOWED_COMPOSE_MODULES = frozenset(
    {
        "test_compose_telemetry.py",
        # The `alert` job's US-14 A-* cases (task 27, #159): compose-marked and
        # deselected by make test/verify, like the telemetry module.
        "test_compose_alert.py",
        # The `responder` job's P-PROD-REFUSAL container form (task 28a, #218).
        "test_compose_responder.py",
        # The `responder` job's P-DEMO-BE full stub loop, run twice (task 28c-C, #233).
        "test_compose_demo_be.py",
    }
)

# Matches the `.compose` marker attribute form (decorator `@pytest.mark.compose`
# or `pytestmark = pytest.mark.compose`), not the bare word "compose" in a
# comment or string.
_COMPOSE_MARKER = re.compile(r"\bmark\.compose\b")

# This guard names the marker in its own allowlist/regex text, so it would match
# itself; it is not a compose module, so exempt it by name explicitly.
_SELF = "test_marker_hygiene.py"


def _tests_dir() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


def test_compose_marker_only_in_allowed_modules() -> None:
    offenders: list[str] = []
    for path in _tests_dir().rglob("test_*.py"):
        if path.name == _SELF or path.name in _ALLOWED_COMPOSE_MODULES:
            continue
        text = path.read_text(encoding="utf-8")
        if _COMPOSE_MARKER.search(text):
            offenders.append(path.name)
    assert not offenders, (
        "the `compose` marker must only appear in the allowed compose modules "
        f"{sorted(_ALLOWED_COMPOSE_MODULES)} (so it cannot silently drop a test "
        f"from `make test`); found it in: {offenders}. If a new compose module "
        "is intended, add it to _ALLOWED_COMPOSE_MODULES in this file."
    )
