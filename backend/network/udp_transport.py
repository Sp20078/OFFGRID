import asyncio
import json
from typing import Any, Callable, Optional


class UDPTransport:
    """
    Lightweight asyncio UDP transport.

    Responsibilities:
    - bind a UDP socket
    - send JSON messages
    - receive JSON messages
    - dispatch received messages to a callback
    """

    def __init__(
        self,
        host: str,
        port: int,
        on_message: Optional[Callable[[dict, tuple], Any]] = None,
    ):
        self.host = host
        self.port = port
        self.on_message = on_message

        self.transport: Optional[asyncio.DatagramTransport] = None
        self.protocol: Optional["UDPProtocol"] = None

    async def start(self):
        loop = asyncio.get_running_loop()

        self.protocol = UDPProtocol(self)

        transport, _ = await loop.create_datagram_endpoint(
            lambda: self.protocol,
            local_addr=(self.host, self.port),
        )

        self.transport = transport

    async def stop(self):
        if self.transport is not None:
            self.transport.close()
            await asyncio.sleep(0)
            self.transport = None

    def send(self, message: dict, host: str, port: int):
        if self.transport is None:
            raise RuntimeError("UDP transport is not running")

        payload = json.dumps(message).encode("utf-8")

        self.transport.sendto(
            payload,
            (host, port),
        )

    def broadcast(self, message: dict, port: int):
        if self.transport is None:
            raise RuntimeError("UDP transport is not running")

        payload = json.dumps(message).encode("utf-8")

        self.transport.sendto(
            payload,
            ("255.255.255.255", port),
        )


class UDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, transport_wrapper: UDPTransport):
        self.transport_wrapper = transport_wrapper

    def connection_made(self, transport):
        self.transport_wrapper.transport = transport

    def datagram_received(self, data: bytes, addr):
        try:
            message = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return

        callback = self.transport_wrapper.on_message

        if callback is None:
            return

        result = callback(message, addr)

        if asyncio.iscoroutine(result):
            asyncio.create_task(result)

    def error_received(self, exc):
        print(f"UDP error: {exc}")

    def connection_lost(self, exc):
        self.transport_wrapper.transport = None