"""P-FLAG-GONE's own correctness (task 29, #161): two fixture trees.

``ci/check_flag_gone.py`` runs only in the production-promotion workflow. Here it
is run as that workflow runs it (a child process, exit status read) against a
tree that must FAIL (the demo defect is present) and a tree that must PASS (it
is gone, the fixtures flag is not set in a production artifact, and the
``require_feeds_allowed`` gate is present). The trees are built per test, so no
fixture file carrying the forbidden strings is committed. No Docker, no network.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

pytestmark = pytest.mark.unit

_SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "ci" / "check_flag_gone.py"

_SETTINGS = "backend/vulntriage/ingest/settings.py"
_MAIN = "backend/vulntriage/main.py"

# A clean tree: the shipped module and gate exist, nothing sets the flag.
_CLEAN = {
    _SETTINGS: "def require_feeds_allowed(environ=None):\n    return 'live'\n",
    _MAIN: "from vulntriage.ingest.settings import require_feeds_allowed\n\n\ndef create_app():\n    require_feeds_allowed()\n",
    "backend/vulntriage/ingest/feeds.py": "FEEDS_FIXTURES = 'fixtures'\n",
    "compose.yaml": "services:\n  backend:\n    environment:\n      DEPLOYMENT_ENVIRONMENT: ${DEPLOYMENT_ENVIRONMENT:-dev}\n",
    "compose.telemetry.yaml": "services:\n  backend:\n    environment:\n      VT_FEEDS: fixtures\n",
    ".env.example": "# VT_FEEDS=fixtures (in .env, not here)\nVT_FEEDS=\n",
    "terraform/server/deploy-env.sh": "# DEPLOYMENT_ENVIRONMENT=prod makes the VT_FEEDS=fixtures refusal fail closed\n",
    "responder/vt_responder/runner.py": 'INTENDED_TEST_FILE = "tests/test_notify_no_fixed_version.py"\n',
    "_docs/testing.md": "VT_DEMO_DEFECT=notify_no_fix is described here; docs are not code.\n",
    "README.md": "VT_DEMO_DEFECT and VT_FEEDS=fixtures are mentioned in prose.\n",
}


def _build(root: pathlib.Path, files: dict[str, str | None]) -> pathlib.Path:
    for rel, text in files.items():
        if text is None:
            (root / rel).unlink()
            continue
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _run(tree: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), str(tree)],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def clean_tree(tmp_path: pathlib.Path) -> pathlib.Path:
    return _build(tmp_path, _CLEAN)


def test_tree_without_the_defect_passes(clean_tree: pathlib.Path) -> None:
    result = _run(clean_tree)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "P-FLAG-GONE: PASS" in result.stdout


@pytest.mark.parametrize(
    ("rel", "text"),
    [
        ("backend/vulntriage/ingest/settings_defect.py", "raw = env.get('VT_DEMO_DEFECT')\n"),
        ("backend/vulntriage/mail/message.py", "if get_demo_defect() == 'notify_no_fix':\n    raise RuntimeError\n"),
        ("backend/vulntriage/mail/errors.py", "class DemoDefectError(Exception):\n    pass\n"),
        ("backend/vulntriage/ingest/consts.py", "DEMO_DEFECT_NOTIFY_NO_FIX = 'x'\n"),
        ("compose.responder.yaml", "      VT_DEMO_DEFECT: ${VT_DEMO_DEFECT:-}\n"),
    ],
)
def test_tree_with_the_defect_fails(clean_tree: pathlib.Path, rel: str, text: str) -> None:
    tree = _build(clean_tree, {rel: text})
    result = _run(tree)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "demo-defect:" in result.stdout
    assert rel in result.stdout
    assert "P-FLAG-GONE: FAIL" in result.stdout


def test_a_defect_file_name_fails(clean_tree: pathlib.Path) -> None:
    tree = _build(clean_tree, {"backend/vulntriage/mail/notify_no_fix.py": "pass\n"})
    result = _run(tree)
    assert result.returncode == 1
    assert "file name backend/vulntriage/mail/notify_no_fix.py" in result.stdout


def test_notify_no_fixed_version_is_a_different_name(clean_tree: pathlib.Path) -> None:
    """The responder's intended test file name contains the token as a prefix only."""
    tree = _build(clean_tree, {"tests/test_notify_no_fixed_version.py": "def test_x():\n    pass\n"})
    assert _run(tree).returncode == 0


def test_docs_and_records_are_not_scanned(clean_tree: pathlib.Path) -> None:
    tree = _build(
        clean_tree,
        {
            "_session-summaries/issue-1.md": "VT_DEMO_DEFECT=notify_no_fix\n",
            "_docs/ai-usage-log.md": "VT_DEMO_DEFECT\n",
            "docs/notes.md": "notify_no_fix\n",
        },
    )
    assert _run(tree).returncode == 0


@pytest.mark.parametrize(
    ("rel", "text"),
    [
        ("compose.yaml", "services:\n  backend:\n    environment:\n      VT_FEEDS: fixtures\n"),
        ("compose.yaml", "services:\n  backend:\n    environment:\n      - VT_FEEDS=fixtures\n"),
        (".env.example", "VT_FEEDS=fixtures\n"),
        ("backend/Dockerfile", "ENV VT_FEEDS=fixtures\n"),
        ("terraform/server/deploy-env.sh", "echo 'VT_FEEDS=fixtures' >> .env\n"),
    ],
)
def test_fixtures_flag_in_a_production_artifact_fails(clean_tree: pathlib.Path, rel: str, text: str) -> None:
    tree = _build(clean_tree, {rel: text})
    result = _run(tree)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "fixtures-flag:" in result.stdout
    assert rel in result.stdout


def test_fixtures_flag_in_a_test_only_override_is_allowed(clean_tree: pathlib.Path) -> None:
    """compose.telemetry.yaml sets fixtures mode by design (it is in the clean tree)."""
    assert "VT_FEEDS: fixtures" in (clean_tree / "compose.telemetry.yaml").read_text(encoding="utf-8")
    assert _run(clean_tree).returncode == 0


@pytest.mark.parametrize(
    ("rel", "text"),
    [
        (_SETTINGS, "# the gate was removed\n"),
        (_MAIN, "from vulntriage.ingest.settings import require_feeds_allowed\n\n# require_feeds_allowed() is not called\n"),
        (_MAIN, None),
    ],
)
def test_missing_refusal_gate_fails(clean_tree: pathlib.Path, rel: str, text: str | None) -> None:
    tree = _build(clean_tree, {rel: text})
    result = _run(tree)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "require_feeds_allowed is not" in result.stdout


def test_bad_usage_exits_2(tmp_path: pathlib.Path) -> None:
    assert _run(tmp_path / "does-not-exist").returncode == 2
