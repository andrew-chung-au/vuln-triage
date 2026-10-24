"""Observability settings, read from the environment at call time.

Follows the backend's per-module ``os.environ`` pattern (``db/session.py``,
``api/service_settings.py``): no central config object, read lazily, never
cached, never logged.
"""

from __future__ import annotations

import os

DEFAULT_SERVICE_NAME = "vulntriage-backend"
DEFAULT_ENVIRONMENT = "dev"


def get_otlp_endpoint() -> str | None:
    """The OTLP exporter endpoint, or None when unset.

    When None, the SDK runs with no exporter (export is a no-op, A40); it still
    creates real span contexts. Honours the standard
    ``OTEL_EXPORTER_OTLP_ENDPOINT`` variable.
    """
    return os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or None


def get_service_name() -> str:
    return os.environ.get("OTEL_SERVICE_NAME") or DEFAULT_SERVICE_NAME


def get_deployment_environment() -> str:
    """`dev` or `prod`; the telemetry `deployment.environment` resource attribute."""
    return os.environ.get("DEPLOYMENT_ENVIRONMENT") or DEFAULT_ENVIRONMENT


def get_service_version() -> str:
    """The deployed image tag (D2: `YYYYMMDD-HHMMSS-shortsha`), or `unknown`.

    Set from the running image's tag at deploy; `unknown` in development.
    """
    return os.environ.get("SERVICE_VERSION") or "unknown"
