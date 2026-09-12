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
        allowed_links: Optional[set] = None,
        bind_host: str = "0.0.0.0",
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
        self.bind_host = bind_host
        # When set (from --links), only these node-id pairs are
        # topology neighbors; otherwise discovery forms a full mesh.
        self.allowed_links = allowed_links

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

        # Peers already announced as offline; prevents re-logging the
        # same offline node every expiry tick (log spam).
        self._offline_logged: set[str] = set()

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

    def advertised_ip(self) -> str:
        """
        The IP we advertise in announcements.

        For a 0.0.0.0 bind (the normal laptop case) that is the
        machine's LAN IP. For a specific bind (loopback tests) it is
        that bind address — advertising the LAN IP for a loopback
        socket would give peers an address they cannot reach.
        """
        if self.bind_host not in ("0.0.0.0", "::", ""):
            return self.bind_host
        return self.local_ip()

    def _announcement(self) -> dict:
        # Gossip: share online peers (up to 32) so the whole mesh
        # learns every node transitively (C becomes visible to A via
        # B even when A never hears C's own broadcast).
        gossip = []

        for peer_id, (ip, port) in list(self.peers.items())[:64]:
            # Never gossip provisional static-peer placeholders; only
            # confirmed identities travel.
            if peer_id.startswith("peer-"):
                continue

            node = self.registry.get(peer_id)

            if node is not None and node.is_online():
                gossip.append([peer_id, ip, port])

            if len(gossip) >= 32:
                break

        return {
            "packet_type": "DISCOVERY",
            "node_id": self.node_id,
            "ip": self.advertised_ip(),
            "udp_port": self.udp_port,
            "api_port": self.api_port,
            "timestamp": time(),
            "protocol_version": PROTOCOL_VERSION,
            "peers": gossip,
        }

    async def _announce_loop(self) -> None:
        """
        Announce to every plausible discovery target.

        - 255.255.255.255          (global broadcast, works on most Wi-Fi LANs)
        - <subnet>.255              (directed broadcast, e.g. 192.168.1.255;
                                    often more reliable than the global one)
        - 127.0.0.1                 (lets several demo nodes share one laptop)
        """
        targets = {"255.255.255.255", "127.0.0.1"}

        subnet_broadcast = self._subnet_broadcast()

        if subnet_broadcast:
            targets.add(subnet_broadcast)

        while self._running:
            # Rebuild EVERY tick: the payload carries a gossip
            # snapshot of currently-known peers, which changes as
            # discovery progresses.
            payload = _dumps(self._announcement())
            for target in targets:
                try:
                    self._send_announcement(payload, target)
                except Exception:
                    logger.exception(
                        "Failed to send discovery announcement to %s", target
                    )

            # Unicast to every known peer's transport port as well:
            # that socket is exclusively bound, so delivery is
            # guaranteed. This self-heals discovery when broadcast is
            # flaky (shared-host REUSEPORT balancing) or blocked by
            # the network entirely.
            for peer_id, (peer_ip, peer_port) in list(self.peers.items()):
                try:
                    self.transport.send_to(payload, (peer_ip, peer_port))
                except Exception:
                    logger.debug("Unicast announcement to %s failed", peer_id)

            await asyncio.sleep(self.announce_interval)

    def _send_announcement(self, payload: bytes, target: str) -> None:
        """
        Send one announcement datagram.

        Uses a fresh ephemeral socket per announcement: with
        SO_REUSEPORT the kernel hashes the 4-tuple to pick one
        listener, and a fixed source port would always land on the
        same process (sometimes our own). A fresh source port makes
        same-machine multi-node demos reliable. On real laptops
        (distinct IPs) any approach works.
        """
        import socket as _socket

        sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)

        try:
            sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_BROADCAST, 1)
            sock.sendto(payload, (target, self.discovery_port))
        finally:
            sock.close()

    def _subnet_broadcast(self) -> Optional[str]:
        """Best-effort x.y.z.255 broadcast address for a /24-style LAN."""
        ip = self.local_ip()

        parts = ip.split(".")

        if len(parts) != 4 or ip.startswith("127."):
            return None

        return f"{parts[0]}.{parts[1]}.{parts[2]}.255"

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

        ip = addr[0] or message.get("ip")
        udp_port = message.get("udp_port") or addr[1]

        if not isinstance(udp_port, int) or not (0 < udp_port < 65536):
            return

        self.register_peer(node_id, ip, int(udp_port))

        # Learn/refresh gossiped peers (second-hand knowledge). New
        # nodes are registered; known ones get their liveness
        # refreshed because a peer we trust recently heard from them.
        for entry in message.get("peers") or []:
            if not isinstance(entry, (list, tuple)) or len(entry) != 3:
                continue

            gossip_id, gossip_ip, gossip_port = entry

            if (
                not isinstance(gossip_id, str)
                or not gossip_id
                or gossip_id.startswith("peer-")
                or gossip_id == self.node_id
                or not isinstance(gossip_port, int)
                or not (0 < gossip_port < 65536)
            ):
                continue

            is_new = self.registry.get(gossip_id) is None

            # Second-hand knowledge: record address but do not fake
            # liveness. The unicast introduction below makes the new
            # peer send US a direct announcement, which is the
            # first-hand confirmation that flips it ONLINE.
            self.register_peer(gossip_id, str(gossip_ip), gossip_port, confirm=False)

            if is_new:
                logger.info(
                    "[DISCOVERY] learned %s at %s:%d via %s gossip",
                    gossip_id,
                    gossip_ip,
                    gossip_port,
                    node_id,
                )

                # Introduce ourselves immediately by unicast so the
                # new peer learns US too — otherwise it only knows us
                # second-hand and (with no direct path) keeps marking
                # us offline while we mark it online. Sent to the
                # peer's transport port (exclusively bound, unlike the
                # shared discovery port).
                try:
                    self.transport.send_to(
                        _dumps(self._announcement()),
                        (str(gossip_ip), gossip_port),
                    )
                except OSError:
                    logger.debug(
                        "Gossip introduction to %s failed", gossip_id
                    )

    def register_peer(
        self,
        node_id: str,
        ip: str,
        udp_port: int,
        confirm: bool = True,
    ) -> None:
        """
        Register or refresh a peer in the shared registry/topology.

        confirm=True  -> first-hand evidence (direct announcement,
                         data packet, or gossip introduction reply):
                         refreshes last_seen / flips ONLINE.
        confirm=False -> second-hand gossip knowledge only: records
                         the address so we can reach the peer, but
                         does NOT fake liveness (no ONLINE flapping
                         for nodes we have never heard from).

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

            if confirm:
                existing.mark_seen()
                self._offline_logged.discard(node_id)
        else:
            node = Node(node_id=node_id, address=ip, port=udp_port)

            if not confirm:
                # Gossip-learned: start OFFLINE until we hear from
                # the node itself.
                node.mark_offline()

            self.registry.add(node)

        self.peers[node_id] = (ip, udp_port)

        # Reconcile provisional static-peer entries: once a real
        # identity is learned for the same ip:port, drop the
        # provisional "peer-ip:port" placeholder everywhere.
        provisional_id = f"peer-{ip}:{udp_port}"

        if provisional_id != node_id:
            provisional = self.registry.get(provisional_id)

            if provisional is not None:
                self.registry.remove(provisional_id)
                self.topology.disconnect(self.node_id, provisional_id)
                self.topology.remove_node(provisional_id)
                self.peers.pop(provisional_id, None)

                for other_id in list(self.peers):
                    if other_id not in (node_id, provisional_id):
                        self.topology.disconnect(provisional_id, other_id)

        # Mesh edge maintenance.
        self.topology.add_node(node_id)

        if self.allowed_links is None:
            # Full mesh: every discovered peer is directly reachable.
            self.topology.connect(self.node_id, node_id)

            for other_id in self.peers:
                if other_id != node_id:
                    self.topology.connect(node_id, other_id)
        else:
            # Configured-links mode (--links): only the given pairs.
            if frozenset((self.node_id, node_id)) in self.allowed_links:
                self.topology.connect(self.node_id, node_id)

            for other_id in self.peers:
                if other_id != node_id and frozenset(
                    (node_id, other_id)
                ) in self.allowed_links:
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

        Their socket addresses are deliberately KEPT in
        self.peers: unicast announcements continue to go to that
        address, so when the laptop comes back (same IP) the very
        next announcement re-registers it and the mesh heals
        itself without waiting for broadcast.

        Returns the node ids that went offline this round.
        """
        # Existing HeartbeatManager marks stale nodes offline.
        self.heartbeats.check_all()

        went_offline: list[str] = []

        for node in self.registry.all_nodes():
            if node.node_id == self.node_id:
                continue

            if node.is_online():
                self._offline_logged.discard(node.node_id)
                continue

            if node.node_id not in self.peers:
                continue

            self.topology.disconnect(self.node_id, node.node_id)

            # Log/announce the transition only once, not every tick.
            if node.node_id not in self._offline_logged:
                self._offline_logged.add(node.node_id)
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
