from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import socket
from typing import Iterator


class EgressViolation(RuntimeError):
    """Raised when a network egress attempt is blocked."""


@dataclass
class OfflineEnforcement:
    attempted: bool = False
    last_error: str | None = None


@contextmanager
def offline_guard(enabled: bool) -> Iterator[OfflineEnforcement]:
    state = OfflineEnforcement()
    if not enabled:
        yield state
        return

    original_socket = socket.socket
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    def _blocked(*args, **kwargs):
        message = "egress violation: outbound network disabled"
        state.attempted = True
        state.last_error = message
        raise EgressViolation(message)

    class BlockedSocket(original_socket):
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            _blocked()

    socket.socket = BlockedSocket  # type: ignore[assignment]
    socket.create_connection = _blocked  # type: ignore[assignment]
    socket.getaddrinfo = _blocked  # type: ignore[assignment]
    try:
        yield state
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection  # type: ignore[assignment]
        socket.getaddrinfo = original_getaddrinfo  # type: ignore[assignment]
