"""The network guard's own tests, U-NET and I-NET.

Each case attempts a real non-loopback call and passes only because the guard
raises ``OutboundNetworkBlocked``. If the guard is disabled, both cases fail.
"""

from __future__ import annotations

import socket
import urllib.request

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from network_guard import OutboundNetworkBlocked


@pytest.mark.unit
def test_u_net_blocks_outbound_socket() -> None:
    with pytest.raises(OutboundNetworkBlocked):
        socket.create_connection(("example.com", 80))


@pytest.mark.sqlite_integration
def test_i_net_blocks_outbound_http(sqlite_session: Session) -> None:
    assert sqlite_session.execute(text("SELECT 1")).scalar_one() == 1
    with pytest.raises(OutboundNetworkBlocked):
        urllib.request.urlopen("http://example.com")
