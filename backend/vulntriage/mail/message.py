"""The owner-notification message: plain-text labelled fields, safe headers,
defanged advisory text (task 37; ``_docs/architecture.md`` § Security
boundaries, A31).

Two guardrails live here, both from the architecture's prompt-injection table:

1. **Header injection.** The Subject and every other header value are built
   from VulnTriage's own finding id and tier only — never from an OSV id, a
   package name, advisory text or any owner-supplied text. A header value that
   contains a CR or LF is rejected (``HeaderInjectionError``): the send fails
   and nothing is delivered. ``build_message`` only ever puts the finding id and
   tier into headers, so the check is a belt-and-braces guard against a future
   caller, and it is exercised directly by a unit test.

2. **URL defanging.** Advisory ``summary``/``details``/``references`` text comes
   from OSV and is untrusted. Before it appears in the body (only under the
   labelled "Advisory summary (untrusted, from OSV):" heading) every URL-like
   token is defanged so a mail client cannot auto-link it: any ``scheme:`` form,
   any ``www.`` token and any domain-shaped token. ``http``/``https`` become
   ``hxxp``/``hxxps``; the ``:`` after a scheme becomes ``[:]``; each ``.`` in a
   host becomes ``[.]`` (``https://a.example/x`` -> ``hxxps[:]//a[.]example/x``;
   ``www.a.example`` -> ``www[.]a[.]example``).

The message is always ``text/plain``; there is no HTML part, so no mail client
renders advisory text as markup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from email.message import EmailMessage


class HeaderInjectionError(ValueError):
    """A header value contained a CR or LF; the send is refused (A31)."""


class DemoDefectError(RuntimeError):
    """The deliberate ``notify_no_fix`` demo defect fired (task 28a / #218).

    The message is a fixed string: no advisory text, owner contact or finding data.
    """


@dataclass(frozen=True)
class OwnerNotification:
    """A ready-to-send owner notification.

    ``sender`` and ``recipient`` are addresses; ``subject`` and ``body`` are the
    already-built header and text. A transport sends this as-is; it does not
    re-build headers or re-run the defang.
    """

    sender: str
    recipient: str
    subject: str
    body: str

    def as_email_message(self) -> EmailMessage:
        """Render to a stdlib ``EmailMessage`` (``text/plain``), headers checked.

        Re-validates the header values as a final gate before handing bytes to a
        transport, so no transport can be given a CR/LF header value.
        """
        _reject_header_control_chars(self.sender)
        _reject_header_control_chars(self.recipient)
        _reject_header_control_chars(self.subject)
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = self.recipient
        msg["Subject"] = self.subject
        msg.set_content(self.body)
        return msg


def _reject_header_control_chars(value: str) -> None:
    """Raise ``HeaderInjectionError`` if ``value`` holds a CR or LF (A31)."""
    if "\r" in value or "\n" in value:
        raise HeaderInjectionError("header value contains a CR or LF")


# -- URL defanging (A31) ----------------------------------------------------

# A scheme followed by its separator: `http://`, `mailto:`, `javascript:`, etc.
# `[a-z][a-z0-9+.-]*` is the RFC 3986 scheme grammar; `:` then optional `//`.
_SCHEME = re.compile(r"(?i)\b([a-z][a-z0-9+.\-]*):(//)?")
# A `www.` token: `www.` then a host-shaped run.
_WWW = re.compile(r"(?i)\bwww\.[a-z0-9.\-]+")
# A domain-shaped token: dot-separated labels ending in an alphabetic TLD,
# optionally with a port and/or a path. Covers bare hosts and the host part of
# an email address (the `@` is handled by matching the host that follows it).
_DOMAIN = re.compile(
    r"(?i)\b(?:[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?\.)+[a-z]{2,}(?::\d+)?(?:/[^\s]*)?"
)


def _defang_host(host: str) -> str:
    """Replace each ``.`` in a host-ish run with ``[.]`` (leaves the path alone)."""
    # Split off a path so dots in the path are not touched (only the host is a
    # link target; `[.]` in a path would be noise). The first `/` starts a path.
    if "/" in host:
        head, _, tail = host.partition("/")
        return head.replace(".", "[.]") + "/" + tail
    return host.replace(".", "[.]")


def defang(text: str) -> str:
    """Return ``text`` with every URL-like token made inert (A31).

    Idempotent enough for one pass over untrusted advisory text: a scheme, any
    ``www.`` token and any domain-shaped token are each neutralised so no mail
    client auto-links them.
    """

    def _scheme_sub(m: re.Match[str]) -> str:
        scheme = m.group(1)
        slashes = m.group(2) or ""
        low = scheme.lower()
        if low == "http":
            scheme = "hxxp" + scheme[4:]
        elif low == "https":
            scheme = "hxxps" + scheme[5:]
        return f"{scheme}[:]{slashes}"

    # Scheme first, so `https://a.example` has its `:` neutralised before the
    # domain pass defangs the host dots.
    text = _SCHEME.sub(_scheme_sub, text)
    text = _WWW.sub(lambda m: _defang_host(m.group(0)), text)
    text = _DOMAIN.sub(lambda m: _defang_host(m.group(0)), text)
    return text


# -- building the message ---------------------------------------------------

_ADVISORY_HEADING = "Advisory summary (untrusted, from OSV):"


def build_message(
    *,
    sender: str,
    recipient: str,
    finding_id: str,
    tier: str,
    package: str | None = None,
    fixed_version: str | None = None,
    advisory_text: str | None = None,
) -> OwnerNotification:
    """Build the plain-text labelled-field owner notification (task 37).

    The Subject is built from the finding id and tier only (A31). Package and
    fixed-version are VulnTriage-controlled labelled fields. ``advisory_text`` is
    untrusted OSV text: it is placed only under the "Advisory summary" heading
    and is defanged first.

    ``finding_id`` and ``tier`` are validated for CR/LF before they reach the
    Subject, so a crafted value fails the send (``HeaderInjectionError``) rather
    than smuggling a header.
    """
    _reject_header_control_chars(finding_id)
    _reject_header_control_chars(tier)

    subject = f"VulnTriage: top-tier finding {finding_id} ({tier}) needs an owner decision"

    lines = [
        "A top-tier (P1) vulnerability finding is assigned to you as the owner.",
        "",
        f"Finding: {finding_id}",
        f"Tier: {tier}",
    ]
    if package is not None:
        lines.append(f"Package: {package}")
    if fixed_version is not None:
        lines.append(f"Fixed version: {fixed_version}")
    else:
        lines.append("Fixed version: none")
    lines.extend(
        [
            "",
            "Please review this finding in VulnTriage and record a fix or a",
            "risk-acceptance decision.",
        ]
    )
    if advisory_text:
        lines.extend(["", _ADVISORY_HEADING, defang(advisory_text)])

    body = "\n".join(lines) + "\n"
    return OwnerNotification(
        sender=sender, recipient=recipient, subject=subject, body=body
    )
