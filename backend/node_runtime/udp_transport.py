"""
Async UDP transport for real LAN communication.

Provides packet send/receive primitives used by the real-node
runtime. Only standard-library networking is used so it works on
Windows and Linux laptops alike.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Optional, Tuple

logger = logging.getLogger("offgrid.udp")

# Maximum UDP payload we accept (bytes). Protects against
# oversized packets and UDP amplification abuse.
MAX_PACKET_BYTES = 60_000

ReceiveHandler = Callable[[bytes, Tuple[str, int]], Awaitable[None]]


class UdpTransport:
    """
    Wraps a single bound UDP socket.

    - bind() starts the receive loop.
    - send_to() sends one datagram to a peer address.
    - stop() closes the socket cleanly.

    Incoming datagrams are validated (size + JSON) and dispatched
    to the provided async handler as (raw_bytes, addr).
    """

    def __init__(self, host: str, port: int, handler: ReceiveHandler):
        self.host = host
        self.port = port  # updated to the bound port by start()
        self.handler = handler

        self._transport: Optional[asyncio.DatagramTransport] = None
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        loop = asyncio.get_running_loop()

        transport, _protocol = await loop.create_datagram_endpoint(
            lambda: _UdpProtocol(self),
            local_addr=(self.host, self.port),
        )

        self._transport = transport
        self._running = True

        # Record the actually bound port (differs from the configured
        # port when binding to port 0 for ephemeral test sockets).
        sockname = transport.get_extra_info("sockname")

        if sockname is not None:
            self.port = int(sockname[1])

        logger.info("UDP transport bound to %s:%d", self.host, self.port)

    async def stop(self) -> None:
        self._running = False

        if self._transport is not None:
            self._transport.close()
            self._transport = None

            logger.info("UDP transport on %s:%d closed", self.host, self.port)

    @property
    def running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def send_to(self, data: bytes, address: Tuple[str, int]) -> bool:
        """
        Send a datagram to a specific address.

        Returns True when the datagram was handed to the OS.
        UDP gives no delivery guarantee; that is what the ACK
        layer and store-and-forward are for.
        """
        if self._transport is None:
            logger.warning("send_to before start(); dropping packet")
            return False

        if len(data) > MAX_PACKET_BYTES:
            logger.warning(
                "Outgoing packet too large (%d bytes); dropping", len(data)
            )
            return False

        try:
            self._transport.sendto(data, address)
            return True
        except OSError as exc:
            logger.warning("UDP send to %s failed: %s", address, exc)
            return False

    def send_json(self, payload: dict[str, Any], address: Tuple[str, int]) -> bool:
        data = json.dumps(payload).encode("utf-8")
        return self.send_to(data, address)

    def send_broadcast(self, data: bytes, port: int) -> bool:
        """
        Send a datagram to the LAN broadcast address.

        Uses SO_BROADCAST which is supported on both Windows
        and Linux. <broadcast> resolves to 255.255.255.255.
        """
        if self._transport is None:
            return False

        try:
            sock = self._transport.get_extra_info("socket")

            if sock is not None:
                import socket as _socket

                if not sock.getsockopt(
                    _socket.SOL_SOCKET, _socket.SO_BROADCAST
                ):
                    sock.setsockopt(
                        _socket.SOL_SOCKET,
                        _socket.SO_BROADCAST,
                        1,
                    )
        except OSError as exc:
            logger.debug("Could not set SO_BROADCAST: %s", exc)

        return self.send_to(data, ("<broadcast>", port))

    # ------------------------------------------------------------------
    # Receiving (called by protocol)
    # ------------------------------------------------------------------

    async def _handle_datagram(self, data: bytes, addr: Tuple[str, int]) -> None:
        if len(data) > MAX_PACKET_BYTES:
            logger.warning("RX oversized packet from %s; dropped", addr)
            return

        try:
            await self.handler(data, addr)
        except Exception:
            # A malformed packet or handler bug must never kill
            # the receive loop.
            logger.exception("RX handler error from %s", addr)


class _UdpProtocol(asyncio.DatagramProtocol):
    def __init__(self, transport: UdpTransport):
        self.transport_ref = transport

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        pass

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        asyncio.ensure_future(self.transport_ref._handle_datagram(data, addr))

    def error_received(self, exc: Exception) -> None:
        logger.debug("UDP protocol error: %s", exc)
