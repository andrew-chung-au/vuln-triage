"""Mail settings, read from the environment at call time (task 37).

Follows the backend's per-module ``os.environ`` pattern (``db/session.py``,
``observability/settings.py``): no central config object, read lazily, never
cached, never logged.

Two settings select and constrain the email route:

- ``MAIL_TRANSPORT`` — ``mailhog`` (dev and ``make test-compose``), ``ses``
  (AWS) or ``memory`` (the in-process recording sink that ``make test`` uses).
  The default is ``memory`` so a test or a misconfigured deploy can never reach
  a real address by accident.
- ``MAIL_SENDER`` — the one verified sender address every message is sent from.
  A send from any other address is refused and nothing is delivered
  (``I-OWNER-SENDER``); in AWS this mirrors the SES role's sender-address
  condition. There is no default: a route that needs it and has none holds the
  job as a configuration error rather than guessing an address.

MailHog's host and port (``MAIL_SMTP_HOST`` / ``MAIL_SMTP_PORT``) default to the
Compose service name and the usual MailHog SMTP port.
"""

from __future__ import annotations

import os

# Transport names. ``memory`` is the in-process recording sink; it is the
# default so nothing reaches a real address unless the environment opts in.
TRANSPORT_MEMORY = "memory"
TRANSPORT_MAILHOG = "mailhog"
TRANSPORT_SES = "ses"

DEFAULT_TRANSPORT = TRANSPORT_MEMORY
DEFAULT_SMTP_HOST = "mailhog"
DEFAULT_SMTP_PORT = 1025


def get_transport_name() -> str:
    """Which mail transport to use: ``memory``, ``mailhog`` or ``ses``."""
    return os.environ.get("MAIL_TRANSPORT") or DEFAULT_TRANSPORT


def get_sender() -> str | None:
    """The one verified sender address every message is sent from, or None.

    When None, a route that needs a sender holds the job rather than guessing.
    """
    return os.environ.get("MAIL_SENDER") or None


def get_smtp_host() -> str:
    """The MailHog SMTP host (the Compose service name by default)."""
    return os.environ.get("MAIL_SMTP_HOST") or DEFAULT_SMTP_HOST


def get_smtp_port() -> int:
    """The MailHog SMTP port (1025 by default)."""
    raw = os.environ.get("MAIL_SMTP_PORT")
    if not raw:
        return DEFAULT_SMTP_PORT
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_SMTP_PORT


def get_ses_region() -> str | None:
    """The AWS region that holds the verified sender identity (SES route).

    VERIFY: the SES region that holds the verified identity (task 37).
    """
    return os.environ.get("AWS_REGION") or None
