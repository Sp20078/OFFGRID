"""
LAN peer discovery over UDP broadcast.

A node periodically announces itself on the discovery port and
listens for other nodes' announcements. Discovered peers are
registered in the existing NodeRegistry (with their real LAN IP)
and connected in the existing NetworkTopology so the existing
BFS Router can route through them.

Discovery messages are small JSON datagrams:

    {
        "packet_type": "DISCOVERY",
        "node_id": "NODE_A",
        "ip": "192.168.1.101",
        "udp_port": 9001,
        "api_port": 8001,
        "timestamp": 1726100000.0,
        "protocol_version": 1
    }
"""

from __future__ import annotations

import asyncio
import logging
import socket
from time import time
from typing import Optional, Tuple

from backend.network.heartbeat import HeartbeatManager
from backend.network.node import Node
from backend.network.registry import NodeRegistry
from backend.network.topology import NetworkTopology

logger = logging.getLogger("offgrid.discovery")

PROTOCOL_VERSION = 1
MAX_DISCOVERY_BYTES = 4096


class DiscoveryService:
    """
    Periodic UDP-broadcast announcer + listener.

    Every announce_interval seconds the service broadcasts its own
    identity on the discovery port. Announcements from other
    OFFGRID nodes are parsed and registered.

    The service is also a heartbeat carrier: any packet received
    from a known peer refreshes its last_seen timestamp.
    """

    def __init__(
        self,
        transport,  # UdpTransport
        node_id: str,
        udp_port: int,
        api_port: Optional[int],
        registry: NodeRegistry,
        topology: NetworkTopology,
        discovery_port: int = 9999,
        announce_interval: float = 2.0,
        heartbeat_timeout: float = 6.0,
    ):
        self.transport = transport
        self.node_id = node_id
        self.udp_port = udp_port
        self.api_port = api_port
        self.registry = registry
        self.topology = topology
        self.discovery_port = discovery_port
        self.announce_interval = announce_interval
        self.heartbeat_timeout = heartbeat_timeout

        self._announce_task: Optional[asyncio.Task] = None
        self._expiry_task: Optional[asyncio.Task] = None
        self._running = False

        # Existing heartbeat expiry logic (reused, not reimplemented).
        self.heartbeats = HeartbeatManager(
            registry=registry,
            timeout=heartbeat_timeout,
        )

        # node_id -> (ip, udp_port) of known peers.
        self.peers: dict[str, Tuple[str, int]] = {}

    # ------------------------------------------------------------------
    # Local address helpers
    # ------------------------------------------------------------------

    @staticmethod
    def local_ip() -> str:
        """
        Best-effort local LAN IP without sending data to the internet.

        Opens a UDP socket towards a private RFC1918 address — no
        packets actually leave the machine, but the OS picks the
        interface it would route through. Falls back gracefully in
        isolated networks.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.connect(("10.255.255.255", 1))
                ip = sock.getsockname()[0]
            finally:
                sock.close()
            return ip
        except OSError:
            return "127.0.0.1"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        self._running = True

        # Register self so topology/registry snapshots include us.
        me = Node(
            node_id=self.node_id,
            address=self.local_ip(),
            port=self.udp_port,
        )
        self.registry.add(me)
        self.topology.add_node(self.node_id)

        self._announce_task = asyncio.create_task(self._announce_loop())
        self._expiry_task = asyncio.create_task(self._expiry_loop())

        logger.info(
            "Discovery started (port %d, interval %.1fs)",
            self.discovery_port,
            self.announce_interval,
        )

    async def stop(self) -> None:
        self._running = False

        for task in (self._announce_task, self._expiry_task):
            if task is not None:
                task.cancel()

        for task in (self._announce_task, self._expiry_task):
            if task is not None:
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    # ------------------------------------------------------------------
    # Announcing
    # ------------------------------------------------------------------

    def _announcement(self) -> dict:
        return {
            "packet_type": "DISCOVERY",
            "node_id": self.node_id,
            "ip": self.registry.get(self.node_id).address
            if self.registry.get(self.node_id)
            else self.local_ip(),
            "udp_port": self.udp_port,
            "api_port": self.api_port,
            "timestamp": time(),
            "protocol_version": PROTOCOL_VERSION,
        }

    async def _announce_loop(self) -> None:
        while self._running:
            try:
                self.transport.send_broadcast(
                    _dumps(self._announcement()),
                    self.discovery_port,
                )
            except Exception:
                logger.exception("Failed to send discovery announcement")

            await asyncio.sleep(self.announce_interval)

    # ------------------------------------------------------------------
    # Receiving
    # ------------------------------------------------------------------

    async def handle_datagram(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        Parse an incoming broadcast and register the peer.

        Malformed packets are rejected silently (log only).
        """
        if len(data) > MAX_DISCOVERY_BYTES:
            return

        try:
            message = _loads(data)
        except (ValueError, UnicodeDecodeError):
            logger.debug("Ignoring malformed discovery datagram from %s", addr)
            return

        if not isinstance(message, dict):
            return

        if message.get("packet_type") != "DISCOVERY":
            return

        if message.get("protocol_version") != PROTOCOL_VERSION:
            logger.debug(
                "Ignoring discovery from %s (protocol version mismatch)", addr
            )
            return

        node_id = message.get("node_id")

        if not isinstance(node_id, str) or not node_id:
            return

        if node_id == self.node_id:
            # Our own broadcast echoed back — ignore.
            return

        ip = message.get("ip") or addr[0]
        udp_port = message.get("udp_port") or addr[1]

        if not isinstance(udp_port, int) or not (0 < udp_port < 65536):
            return

        self.register_peer(node_id, ip, int(udp_port))

    def register_peer(self, node_id: str, ip: str, udp_port: int) -> None:
        """
        Register or refresh a peer in the shared registry/topology.

        Also updates topology edges for all known peers of that node:
        in real mode a discovered node is directly reachable, so it
        gains an edge to every peer we know about (full mesh by
        default; restricted by RuntimeConfig.links when provided).
        """
        existing = self.registry.get(node_id)
        is_new = existing is None

        if existing is not None:
            existing.address = ip
            existing.port = udp_port
            existing.mark_seen()
        else:
            self.registry.add(
                Node(node_id=node_id, address=ip, port=udp_port)
            )

        self.peers[node_id] = (ip, udp_port)

        # Mesh edge maintenance.
        self.topology.add_node(node_id)
        self.topology.connect(self.node_id, node_id)

        for other_id in self.peers:
            if other_id != node_id:
                self.topology.connect(node_id, other_id)

        if is_new:
            logger.info(
                "[DISCOVERY] discovered %s at %s:%d", node_id, ip, udp_port
            )

    # ------------------------------------------------------------------
    # Heartbeat expiry
    # ------------------------------------------------------------------

    async def _expiry_loop(self) -> None:
        while self._running:
            await asyncio.sleep(1.0)

            # This node is alive by definition; refresh it so the
            # shared HeartbeatManager never expires ourselves.
            me = self.registry.get(self.node_id)

            if me is not None:
                me.mark_seen()

            self.expire_stale_peers()

    def expire_stale_peers(self) -> list[str]:
        """
        Mark peers that have not been heard from as OFFLINE and
        disconnect them from the topology so routing avoids them.

        Returns the node ids that went offline this round.
        """
        # Existing HeartbeatManager marks stale nodes offline.
        self.heartbeats.check_all()

        went_offline: list[str] = []

        for node in self.registry.all_nodes():
            if node.node_id == self.node_id:
                continue

            if node.is_online() or node.node_id not in self.peers:
                continue

            self.topology.disconnect(self.node_id, node.node_id)
            self.peers.pop(node.node_id, None)
            went_offline.append(node.node_id)

            logger.warning("[HEARTBEAT] %s offline (timeout)", node.node_id)

        return went_offline

    # ------------------------------------------------------------------
    # Heartbeat bookkeeping for data-plane packets
    # ------------------------------------------------------------------

    def record_heartbeat(self, node_id: str) -> None:
        """
        Any valid DATA/ACK/HEARTBEAT packet from a peer counts as
        evidence that the peer is alive.
        """
        node = self.registry.get(node_id)

        if node is not None:
            node.mark_seen()

            if node_id not in self.peers:
                self.peers[node_id] = (node.address, node.port)

            self.topology.connect(self.node_id, node_id)


# Minimal JSON helpers kept local so discovery never depends on
# the packet model (which it must not parse).
import json  # noqa: E402


def _dumps(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _loads(data: bytes) -> dict:
    return json.loads(data.decode("utf-8"))
