"""Mail transports (task 37): one interface, three implementations.

``MailTransport`` is the interface the delivery worker sends through. Every
implementation enforces the same rule: a send whose ``From`` is not the
transport's configured verified sender is refused with ``SenderNotVerifiedError``
and nothing is delivered (``I-OWNER-SENDER``; the AWS SES role carries the same
condition on the sender address).

- ``RecordingTransport`` — the in-process fake sink ``make test`` uses. It
  records the messages it is given and sends nothing over a network, so the
  owner-notification cases stay in the ``sqlite-integration`` job (no Docker).
- ``MailHogTransport`` — SMTP to the MailHog service in the Compose stack
  (``make test-compose`` and local dev). Uses the standard-library ``smtplib``,
  so it adds no dependency. MailHog accepts any recipient and exposes received
  mail over its HTTP API on 8025.
- ``SesTransport`` — Amazon SES on AWS. VERIFY-marked and never exercised in
  CI: it imports ``boto3`` lazily inside ``send`` so no ``make test`` /
  ``make verify`` path imports it, and the dependency is added only when the
  human wires up the AWS route.

``build_transport`` selects one from the mail settings; the delivery worker uses
it, and tests inject ``RecordingTransport`` directly.
"""

from __future__ import annotations

import smtplib
from typing import Protocol, runtime_checkable

from vulntriage.mail import settings
from vulntriage.mail.message import OwnerNotification


class SenderNotVerifiedError(Exception):
    """A send used a From address other than the configured verified sender."""


class MailConfigurationError(Exception):
    """The selected transport is missing required configuration (e.g. no sender)."""


@runtime_checkable
class MailTransport(Protocol):
    """Sends one owner notification, or refuses it.

    An implementation MUST refuse (``SenderNotVerifiedError``) any message whose
    ``sender`` is not its verified sender, delivering nothing.
    """

    @property
    def verified_sender(self) -> str: ...

    def send(self, message: OwnerNotification) -> None: ...


def _check_sender(verified_sender: str, message: OwnerNotification) -> None:
    """Refuse a message that is not from the one verified sender (A31, SES)."""
    if message.sender != verified_sender:
        raise SenderNotVerifiedError(
            "message sender is not the configured verified sender"
        )


class RecordingTransport:
    """In-process sink for ``make test``: records messages, sends nothing.

    Implements the same interface as the MailHog and SES transports and keeps
    every message it accepted in ``sent`` (after the verified-sender check), so
    a test can assert exactly one message reached the owner.
    """

    def __init__(self, verified_sender: str) -> None:
        self._verified_sender = verified_sender
        self.sent: list[OwnerNotification] = []

    @property
    def verified_sender(self) -> str:
        return self._verified_sender

    def send(self, message: OwnerNotification) -> None:
        _check_sender(self._verified_sender, message)
        # Render once so a CR/LF header value is rejected here too (A31).
        message.as_email_message()
        self.sent.append(message)


class MailHogTransport:
    """SMTP delivery to MailHog (dev and ``make test-compose``).

    Uses ``smtplib`` (standard library, no new dependency). MailHog has no auth
    and accepts any recipient; received mail is read over its HTTP API on 8025.
    """

    def __init__(self, verified_sender: str, host: str, port: int) -> None:
        self._verified_sender = verified_sender
        self._host = host
        self._port = port

    @property
    def verified_sender(self) -> str:
        return self._verified_sender

    def send(self, message: OwnerNotification) -> None:
        _check_sender(self._verified_sender, message)
        email_message = message.as_email_message()
        with smtplib.SMTP(self._host, self._port, timeout=10) as smtp:
            smtp.send_message(email_message)


class SesTransport:
    """Amazon SES delivery on AWS (VERIFY; not exercised in CI).

    Imports ``boto3`` lazily inside :meth:`send` so no ``make test`` /
    ``make verify`` path imports it and the dependency is added only when the
    human wires up the AWS route. The instance role is send-only, limited to the
    one verified sender identity and conditioned on the sender address, so SES
    itself also refuses a send from any other address; the ``_check_sender``
    guard refuses it first so behaviour matches the other transports in tests.

    VERIFY (settle at the human's AWS step, task 37):
    - the IAM action (``ses:SendEmail``, and whether ``ses:SendRawEmail`` is also
      needed), the resource form (the verified identity ARN) and the
      ``ses:FromAddress`` condition key for the role;
    - the SES region that holds the verified identity;
    - the SES sandbox rule that recipients must be verified, and the free
      allowance / sending limits;
    - the exact ``boto3`` client call (``send_raw_email`` vs ``send_email``).
    """

    def __init__(self, verified_sender: str, region: str | None) -> None:
        self._verified_sender = verified_sender
        self._region = region

    @property
    def verified_sender(self) -> str:
        return self._verified_sender

    def send(self, message: OwnerNotification) -> None:
        _check_sender(self._verified_sender, message)
        email_message = message.as_email_message()
        # VERIFY: boto3 is a new dependency added at the AWS step; it is imported
        # here so no test/verify path needs it.
        import boto3  # noqa: PLC0415  (lazy by design; VERIFY the client call)

        client = boto3.client("ses", region_name=self._region)
        # VERIFY: send_raw_email vs send_email and the exact argument shape.
        client.send_raw_email(
            Source=message.sender,
            Destinations=[message.recipient],
            RawMessage={"Data": email_message.as_bytes()},
        )


def build_transport() -> MailTransport:
    """Select the mail transport from the environment (``MAIL_TRANSPORT``).

    Raises ``MailConfigurationError`` when a route is selected with no verified
    sender, so the delivery worker holds the job (``held: configuration error``)
    rather than guessing a sender address.
    """
    name = settings.get_transport_name()
    sender = settings.get_sender()
    if sender is None:
        raise MailConfigurationError("MAIL_SENDER is not set")
    if name == settings.TRANSPORT_MEMORY:
        return RecordingTransport(sender)
    if name == settings.TRANSPORT_MAILHOG:
        return MailHogTransport(sender, settings.get_smtp_host(), settings.get_smtp_port())
    if name == settings.TRANSPORT_SES:
        return SesTransport(sender, settings.get_ses_region())
    raise MailConfigurationError(f"unknown MAIL_TRANSPORT {name!r}")
