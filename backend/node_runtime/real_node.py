"""
RealNode: the control plane of one real OFFGRID node.

Wires together the existing OFFGRID building blocks:

- NodeRegistry / NetworkTopology / Router  (existing network core)
- DeliveryManager / Message / MessageStore (existing messaging)
- UdpTransport                             (real sockets)
- DiscoveryService                         (LAN discovery + heartbeats)
- PacketRelay                              (real multi-hop forwarding)

The existing in-memory demo (backend/api/app.py) is untouched; this
module is the REAL LAN MODE runtime.

Logging note: all runtime components log under the "offgrid.*"
namespace. RealNode attaches a ring-buffer handler so the same
log lines shown on the console ([DISCOVERY], [TX], [RX],
[DELIVERED], ...) are available to the API/dashboard.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import deque
from datetime import datetime, timezone
from time import time
from typing import Any, Deque, List, Optional, Tuple

from backend.messaging.delivery import DeliveryManager
from backend.messaging.message import MessageStatus
from backend.network.node import Node
from backend.network.registry import NodeRegistry
from backend.network.router import Router
from backend.network.topology import NetworkTopology

from .discovery import DiscoveryService
from .relay import PacketRelay, RelayTransportAdapter
from .udp_transport import UdpTransport

logger = logging.getLogger("offgrid.node")

# Fixed demo positions so the existing dashboard graph layout works.
POSITIONS: dict[str, Tuple[float, float]] = {
    "NODE_A": (10.0, 50.0),
    "NODE_B": (30.0, 25.0),
    "NODE_C": (50.0, 50.0),
    "NODE_D": (70.0, 25.0),
    "NODE_E": (90.0, 50.0),
}


class _EventRingHandler(logging.Handler):
    """Captures offgrid.* log records into a bounded event ring."""

    def __init__(self, ring: Deque[dict[str, Any]], limit: int = 200):
        super().__init__(level=logging.INFO)
        self.ring = ring
        self.limit = limit

    def emit(self, record: logging.LogRecord) -> None:
        event = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "nodeId": getattr(record, "node_id", None),
        }
        self.ring.append(event)

        if len(self.ring) > self.limit:
            del self.ring[: len(self.ring) - self.limit]


class RealNode:
    """
    One physical OFFGRID node.

    Lifecycle:

        node = RealNode(config)
        await node.start()   # binds UDP, starts discovery/relay/API
        ...
        await node.stop()
    """

    def __init__(
        self,
        node_id: str,
        host: str = "0.0.0.0",
        udp_port: int = 9001,
        discovery_port: int = 9999,
        api_host: str = "0.0.0.0",
        api_port: Optional[int] = None,
        static_peers: Optional[List[Tuple[str, int]]] = None,
        links: Optional[List[Tuple[str, str]]] = None,
        heartbeat_interval: float = 2.0,
        heartbeat_timeout: float = 6.0,
        max_retries: int = 5,
    ):
        self.node_id = node_id
        self.host = host
        self.udp_port = udp_port
        self.discovery_port = discovery_port
        self.api_host = api_host
        self.api_port = api_port
        self.static_peers = static_peers or []
        self.links = links
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout

        # ----------------------------------------------------------
        # Existing network core
        # ----------------------------------------------------------
        self.registry = NodeRegistry()
        self.topology = NetworkTopology()
        self.router = Router(topology=self.topology, registry=self.registry)

        # ----------------------------------------------------------
        # Real transport + services
        # ----------------------------------------------------------
        self.transport = UdpTransport(host, udp_port, self._handle_datagram)

        # Dedicated listener for the shared discovery port: discovery
        # announcements are broadcast to the well-known discovery port
        # and every node must receive them. Each node's *transport*
        # socket (data plane) stays on its own udp_port.
        self._discovery_socket = UdpTransport(
            host,
            discovery_port,
            self._handle_datagram,
            reuse=True,
        )

        self.discovery = DiscoveryService(
            transport=self.transport,
            node_id=node_id,
            udp_port=udp_port,
            api_port=api_port,
            registry=self.registry,
            topology=self.topology,
            discovery_port=discovery_port,
            announce_interval=heartbeat_interval,
            heartbeat_timeout=heartbeat_timeout,
            allowed_links=frozenset(frozenset(pair) for pair in links) if links else None,
        )

        # ----------------------------------------------------------
        # Existing messaging engine + real forwarding
        # ----------------------------------------------------------
        self.relay = PacketRelay(
            node_id=node_id,
            transport=self.transport,
            discovery=self.discovery,
            router=self.router,
        )

        self.delivery_manager = DeliveryManager(
            router=RelayTransportAdapter(self.relay),
            max_retries=max_retries,
        )
        self.relay.delivery_manager = self.delivery_manager

        # Message-id dedupe on the receiving side (retransmissions
        # create a new packet_id but reuse the same message_id).
        self._delivered_message_ids: set[str] = set()

        # Event ring fed from the offgrid.* log namespace.
        self.events: Deque[dict[str, Any]] = deque(maxlen=200)
        self._ring_handler = _EventRingHandler(self.events)
        logging.getLogger("offgrid").addHandler(self._ring_handler)
        if not logging.getLogger("offgrid").level:
            logging.getLogger("offgrid").setLevel(logging.INFO)

        self._tasks: List[asyncio.Task] = []
        self._api_server: Any = None
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        if self._running:
            return

        await self.transport.start()

        # Bind the shared discovery listener (best-effort: if another
        # process holds the port without SO_REUSEPORT — e.g. on
        # Windows — continue without it; discovery then relies on
        # static peers or unicast to our transport port).
        try:
            await self._discovery_socket.start()
        except OSError as exc:
            logger.warning(
                "[DISCOVERY] could not bind shared port %d (%s); "
                "relying on static peers / unicast",
                self.discovery_port,
                exc,
            )

        await self.discovery.start()

        # Register self in the shared registry (node identity is the
        # logical node_id; the address is this machine's LAN IP).
        me = Node(
            node_id=self.node_id,
            address=DiscoveryService.local_ip(),
            port=self.udp_port,
        )
        self.registry.add(me)

        # Optional manually-shaped topology edges (demo chain mode).
        for node_a, node_b in self.links or []:
            self.topology.connect(node_a, node_b)

        # Static peers: register directly (fallback when broadcast
        # discovery is blocked by the network).
        for peer_ip, peer_port in self.static_peers:
            self._register_static_peer(peer_ip, peer_port)

        self._running = True

        self._tasks.append(asyncio.create_task(self._flush_pending_loop()))
        self._tasks.append(asyncio.create_task(self._retransmit_loop()))

        if self.api_port is not None:
            await self._start_api()

        logger.info(
            "[NODE] %s online  ip=%s  udp=%s:%d  discovery=%d  api=%s",
            self.node_id,
            me.address,
            me.address,
            self.udp_port,
            self.discovery_port,
            f"{me.address}:{self.api_port}" if self.api_port else "disabled",
        )

    async def stop(self) -> None:
        if not self._running:
            return

        self._running = False
        for task in self._tasks:
            task.cancel()

        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()

        if self._api_server is not None:
            self._api_server.should_exit = True
            self._api_server = None

        await self.discovery.stop()
        await self._discovery_socket.stop()
        await self.transport.stop()

        logger.info("[NODE] %s stopped", self.node_id)

    async def _start_api(self) -> None:
        import uvicorn

        from backend.api.real_api import create_app

        app = create_app(self)

        config = uvicorn.Config(
            app,
            host=self.api_host,
            port=self.api_port,
            log_level="warning",
        )

        self._api_server = uvicorn.Server(config)
        self._tasks.append(asyncio.create_task(self._api_server.serve()))

    def _register_static_peer(self, ip: str, port: int) -> None:
        """
        Register a static peer whose node_id is unknown until the
        first discovery/hello arrives. We pre-connect it into the
        topology using a provisional id so routing can start
        immediately; discovery will reconcile identities.
        """
        provisional_id = f"peer-{ip}:{port}"

        if self.registry.get(provisional_id) is None:
            self.registry.add(Node(node_id=provisional_id, address=ip, port=port))
            self.topology.add_node(provisional_id)

            # In demo-chain mode static peers are assumed adjacent.
            if not self.links:
                self.topology.connect(self.node_id, provisional_id)

            self.discovery.peers[provisional_id] = (ip, port)

    # ------------------------------------------------------------------
    # Packet dispatch (single entry point from the UDP transport)
    # ------------------------------------------------------------------

    async def _handle_datagram(self, data: bytes, addr: Tuple[str, int]) -> None:
        from backend.network.packet import PACKET_TYPE_DISCOVERY, Packet

        # Parse once; discovery announcements and data packets share
        # the same JSON-over-UDP wire format.
        try:
            message = json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            logger.warning("[RX] malformed packet from %s; dropped", addr)
            return

        if not isinstance(message, dict):
            return

        if message.get("packet_type") == "DISCOVERY":
            await self.discovery.handle_datagram(data, addr)
            return

        try:
            packet = Packet.from_dict(message)
        except ValueError:
            logger.warning("[RX] malformed packet from %s; dropped", addr)
            return

        if packet.packet_type == PACKET_TYPE_DISCOVERY:
            await self.discovery.handle_datagram(data, addr)
            return

        logger.info(
            "[RX] packet %s type=%s %s -> %s from %s",
            packet.packet_id[:8],
            packet.packet_type,
            packet.source,
            packet.destination,
            addr[0],
        )

        await self.relay.handle_packet(packet, addr)

    # ------------------------------------------------------------------
    # Background loops
    # ------------------------------------------------------------------

    async def _flush_pending_loop(self) -> None:
        """
        Store-and-forward: whenever a destination (re)appears,
        retry every message queued for it.
        """
        while self._running:
            await asyncio.sleep(2.0)

            try:
                for node in self.registry.online_nodes():
                    if node.node_id == self.node_id:
                        continue

                    delivered = self.delivery_manager.retry_pending(node.node_id)

                    for message_id in delivered:
                        logger.info(
                            "[STORE-FORWARD] queued message %s delivered to %s",
                            message_id[:8],
                            node.node_id,
                        )
            except Exception:
                logger.exception("Pending flush iteration failed")

    async def _retransmit_loop(self) -> None:
        """
        ACK/retry: periodically re-send FORWARDED messages that have
        not been acknowledged yet (lost packet or lost ACK).
        """
        while self._running:
            await asyncio.sleep(5.0)

            try:
                for message in self.delivery_manager.store.all():
                    if message.status != MessageStatus.FORWARDED:
                        continue

                    if self.delivery_manager.get_retry_count(
                        message.message_id
                    ) >= self.delivery_manager.max_retries:
                        continue

                    self.delivery_manager.retry_message(message)
            except Exception:
                logger.exception("Retransmit iteration failed")

    def udp_port_actual(self) -> int:
        """
        The actually bound UDP port (== udp_port in production; may
        differ in tests that bind to port 0).
        """
        return self.transport.port

    # ------------------------------------------------------------------
    # Public messaging API (used by the FastAPI layer)
    # ------------------------------------------------------------------

    def send_custom_message(self, destination: str, payload: str, ttl: int = 10) -> dict[str, Any]:
        """
        Create a message with the existing DeliveryManager and push
        it onto the real network.

        Returns a status dict: DELIVERED/FAILED with route info.
        The message only becomes DELIVERED (confirmed) when the
        destination's ACK arrives.
        """
        message = self.delivery_manager.create_message(
            source=self.node_id,
            destination=destination,
            payload=payload,
            ttl=ttl,
        )

        sent = self.delivery_manager.deliver(message)

        route = self.relay.find_route(self.node_id, destination) or []

        if sent:
            return {
                "status": "FORWARDED",
                "message_id": message.message_id,
                "source": self.node_id,
                "destination": destination,
                "payload": payload,
                "route": route,
            }

        return {
            "status": "PENDING",
            "message_id": message.message_id,
            "source": self.node_id,
            "destination": destination,
            "payload": payload,
            "route": [],
        }

    def receive_message(self, message) -> str:
        """Feed an inbound message through the existing receive path."""
        self._delivered_message_ids.add(message.message_id)
        return self.delivery_manager.receive(message)

    def confirm_delivery(self, message_id: str) -> bool:
        """Called when an ACK arrives (see PacketRelay._handle_ack)."""
        acknowledged = self.delivery_manager.acknowledge(message_id)

        if acknowledged:
            self._delivered_message_ids.add(message_id)

        return acknowledged

    # ------------------------------------------------------------------
    # Dashboard snapshot (shapes match the existing frontend types)
    # ------------------------------------------------------------------

    def _display_label(self, node_id: str) -> str:
        suffix = node_id.replace("NODE_", "")
        return f"Node {suffix}" if suffix else node_id

    def _route_for_dashboard(self) -> List[str]:
        if not self.registry.online_count():
            return []

        preferred = ["NODE_E", "NODE_D", "NODE_C", "NODE_B"]

        for target in preferred:
            if target == self.node_id:
                continue

            if self.topology.has_node(target):
                route = self.router.find_route(self.node_id, target)

                if route:
                    return route

        return []

    def snapshot(self) -> dict[str, Any]:
        nodes: List[dict[str, Any]] = []

        for node in self.registry.all_nodes():
            is_self = node.node_id == self.node_id
            online = is_self or node.is_online()

            stored = len(
                self.delivery_manager.queue.get_for_destination(node.node_id)
            )

            x, y = POSITIONS.get(node.node_id, (50.0, 50.0))

            nodes.append(
                {
                    "id": node.node_id,
                    "label": self._display_label(node.node_id),
                    "status": "ONLINE" if online else "OFFLINE",
                    "ip": node.address,
                    "latencyMs": 15.0 if online else 0.0,
                    "storedPacketsCount": stored,
                    "x": x,
                    "y": y,
                    "neighbors": self.topology.neighbors(node.node_id),
                    "lastSeenMs": int((time() - node.last_seen) * 1000)
                    if not is_self
                    else 0,
                }
            )

        links: List[dict[str, Any]] = []
        seen: set[Tuple[str, str]] = set()

        for source, neighbors in self.topology.get_graph().items():
            for target in neighbors:
                key = tuple(sorted((source, target)))

                if key in seen:
                    continue

                seen.add(key)

                source_node = self.registry.get(source)
                target_node = self.registry.get(target)

                source_online = (
                    source_node.is_online() if source_node else False
                ) or source == self.node_id
                target_online = (
                    target_node.is_online() if target_node else False
                ) or target == self.node_id

                active = source_online and target_online

                links.append(
                    {
                        "source": source,
                        "target": target,
                        "active": active,
                        "quality": 1.0 if active else 0.0,
                    }
                )

        online_count = sum(1 for n in nodes if n["status"] == "ONLINE")

        metrics = {
            "totalNodes": len(nodes),
            "activeNodes": online_count,
            "activeLinksCount": sum(1 for l in links if l["active"]),
            "activePathHops": self._route_for_dashboard(),
            "internetAvailable": False,
            "storeAndForwardQueueSize": self.delivery_manager.queue.size(),
            "avgMeshLatencyMs": 15.0 if online_count else 0.0,
            "forwardedPackets": self.relay.stats["forwarded_packets"],
            "deliveredPackets": self.relay.stats["delivered_packets"],
        }

        return {
            "nodeId": self.node_id,
            "mode": "real",
            "nodes": nodes,
            "links": links,
            "activeRoute": metrics["activePathHops"],
            "metrics": metrics,
            "logs": list(self.events)[-100:],
            "internetOnline": False,
            "inbox": list(self.relay.inbox)[-50:],
            "pendingMessages": [
                m.to_dict() for m in self.delivery_manager.pending_messages()
            ],
        }
