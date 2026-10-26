"""The responder Compose job (task 28 / #160): `P-PROD-REFUSAL` container form (#218).

Runs under ``make test-compose JOB=responder`` once task 28c wires that job.
Marked ``compose`` and DESELECTED by ``make test`` / ``make verify``. This
module was written WITHOUT being run: the sandbox has no Docker and no
ghcr.io access, so the container form is unverified until CI or a Docker host
runs it (VERIFY: the ``docker compose run`` flags below).

It asserts the RUNNING PROCESS, not only the in-code check: the backend
container is started with the production configuration
(``DEPLOYMENT_ENVIRONMENT=prod``) and ``VT_DEMO_DEFECT=notify_no_fix``; it must
exit non-zero and log the configuration error. A control run in dev must NOT
exit with that error.
"""

from __future__ import annotations

import os
import subprocess

import pytest

pytestmark = pytest.mark.compose

_PROJECT = os.environ.get("VT_COMPOSE_PROJECT", "vt-responder")


def _run_backend(deployment_environment: str) -> subprocess.CompletedProcess[str]:
    """Run the backend image once with the defect set; return the finished process.

    ``--no-deps`` keeps the db out of it (the refusal happens at import, before
    any database use); ``-e`` overrides are per-run so no compose file changes.
    The command imports the app exactly as uvicorn does.
    """
    return subprocess.run(
        [
            "docker", "compose", "-p", _PROJECT, "-f", "compose.yaml",
            "run", "--rm", "--no-deps",
            "-e", "VT_DEMO_DEFECT=notify_no_fix",
            "-e", f"DEPLOYMENT_ENVIRONMENT={deployment_environment}",
            "backend", "python", "-c", "import vulntriage.main",
        ],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def test_p_prod_refusal_container_exits_non_zero_and_logs_the_error() -> None:
    result = _run_backend("prod")
    assert result.returncode != 0, result.stdout + result.stderr
    output = result.stdout + result.stderr
    assert "DemoDefectConfigurationError" in output
    assert "VT_DEMO_DEFECT" in output


def test_p_prod_refusal_container_control_dev_starts() -> None:
    """Control: the same image and variable in dev does not hit the refusal."""
    result = _run_backend("dev")
    assert "DemoDefectConfigurationError" not in result.stdout + result.stderr
    assert result.returncode == 0, result.stdout + result.stderr
