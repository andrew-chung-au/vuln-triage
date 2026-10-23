"""Block outbound network access for the whole test run.

The guard is installed by ``tests/conftest.py`` in ``pytest_configure`` and
restored in ``pytest_unconfigure``. Loopback addresses stay allowed so later
in-process tests can talk to a local server; every other DNS lookup and
non-loopback connect raises :class:`OutboundNetworkBlocked`.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Any

_LOOPBACK_NAMES = {"localhost", "localhost.localdomain"}

_real_getaddrinfo = socket.getaddrinfo
_real_connect = socket.socket.connect
_installed = False


class OutboundNetworkBlocked(RuntimeError):
    """Raised when a test tries to reach a non-loopback host."""


def _normalise_host(host: str | bytes | None) -> str:
    if host is None:
        return ""
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    name = host.strip().lower()
    if name.startswith("[") and name.endswith("]"):
        name = name[1:-1]
    return name.split("%", 1)[0]


def _is_loopback_host(host: str | bytes | None) -> bool:
    name = _normalise_host(host)
    if not name:
        return True
    if name in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


def _blocked(operation: str, host: str | bytes | None) -> OutboundNetworkBlocked:
    shown = _normalise_host(host) or "<unspecified>"
    return OutboundNetworkBlocked(
        f"outbound network is blocked in tests: {operation} to {shown!r}"
    )


def _guarded_getaddrinfo(host: Any, port: Any, *args: Any, **kwargs: Any) -> Any:
    if not _is_loopback_host(host):
        raise _blocked("getaddrinfo", host)
    return _real_getaddrinfo(host, port, *args, **kwargs)


def _guarded_connect(sock: socket.socket, address: Any) -> Any:
    if sock.family in (socket.AF_INET, socket.AF_INET6):
        host = address[0] if isinstance(address, tuple) else address
        if not _is_loopback_host(host):
            raise _blocked("connect", host)
    return _real_connect(sock, address)


def install_network_guard() -> None:
    """Install the guard once for the current process."""
    global _installed
    if _installed:
        return
    socket.getaddrinfo = _guarded_getaddrinfo
    socket.socket.connect = _guarded_connect
    _installed = True


def restore_network_guard() -> None:
    """Restore the original socket functions after the test run."""
    global _installed
    socket.getaddrinfo = _real_getaddrinfo
    socket.socket.connect = _real_connect
    _installed = False
