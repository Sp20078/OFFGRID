"""
Real packet forwarding over UDP.

The relay is the data plane of a real OFFGRID node:

- receives packets from the UDP transport
- drops duplicates via the existing DuplicateDetector
- delivers packets addressed to this node
- otherwise decrements TTL, finds the next hop with the existing
  BFS Router, and forwards the packet over a real socket

Origin-side delivery status (PENDING / FORWARDED / DELIVERED) and
store-and-forward reuse the existing DeliveryManager through
RelayTransportAdapter, which satisfies the existing
MessageTransport protocol.
"""

from __future__ import annotations

import logging
from collections import deque
from time import time
from typing import Any, Deque, List, Optional, Tuple

from backend.messaging.duplicate import DuplicateDetector
from backend.messaging.message import Message
from backend.messaging.transport import MessageTransport
from backend.network.packet import (
    PACKET_TYPE_ACK,
    PACKET_TYPE_DATA,
    Packet,
)

logger = logging.getLogger("offgrid.relay")

DEFAULT_PACKET_TTL = 10

RelayAddress = Tuple[str, int]


class PacketRelay:
    """
    Forwarding engine for one real node.

    Dependencies are the existing OFFGRID classes:

    - router: backend.network.router.Router (BFS, offline-aware)
    - discovery: node_runtime.discovery.DiscoveryService (peer addresses)
    - transport: node_runtime.udp_transport.UdpTransport (real sockets)
    """

    def __init__(
        self,
        node_id: str,
        transport,
        discovery,
        router,
        delivery_manager=None,
        inbox_size: int = 200,
    ):
        self.node_id = node_id
        self.transport = transport
        self.discovery = discovery
        self.router = router
        self.delivery_manager = delivery_manager

        # Packet-level duplicate protection (existing class).
        self.duplicates = DuplicateDetector()

        # Messages delivered to THIS node, newest last.
        self.inbox: Deque[dict[str, Any]] = deque(maxlen=inbox_size)

        # message_ids already delivered locally (bounded) so a
        # retransmission after a lost ACK is re-ACKed but not
        # double-delivered.
        self._delivered_message_ids: set[str] = set()

        # Counters surfaced through the API.
        self.stats = {
            "tx_packets": 0,
            "rx_packets": 0,
            "forwarded_packets": 0,
            "delivered_packets": 0,
            "duplicates_dropped": 0,
            "expired_dropped": 0,
            "route_failures": 0,
        }

    # ------------------------------------------------------------------
    # Route lookup (used by RelayTransportAdapter as well)
    # ------------------------------------------------------------------

    def find_route(self, source: str, destination: str) -> Optional[List[str]]:
        if self.router is None:
            return None

        return self.router.find_route(source, destination)

    def next_hop_address(self, destination: str) -> Optional[RelayAddress]:
        """
        Resolve the real socket address of the next hop towards a
        destination, or None when unknown.
        """
        route = self.find_route(self.node_id, destination)

        if not route or len(route) < 2:
            return None

        return self.discovery.peers.get(route[1])

    # ------------------------------------------------------------------
    # Origin-side sending
    # ------------------------------------------------------------------

    def send_message(self, message: Message, route: Optional[List[str]] = None) -> bool:
        """
        Put a message on the wire as a DATA packet.

        Preferred: unicast to the BFS route's next hop. Fallback
        when no full route is known: flood a copy to every direct
        neighbor (mesh flooding) and let hop-by-hop routing take
        over. Duplicate detection plus TTL keep floods bounded.
        """
        route = route or self.find_route(message.source, message.destination)

        packet = Packet(
            source=message.source,
            destination=message.destination,
            payload={
                "kind": "MESSAGE",
                "message_id": message.message_id,
                "text": message.payload,
                "via": [],
            },
            ttl=message.ttl if message.ttl > 0 else DEFAULT_PACKET_TTL,
            packet_type=PACKET_TYPE_DATA,
        )

        # Mark our own packet as seen so flooded echoes come back
        # as duplicates instead of being processed.
        self.duplicates.mark_seen(packet.packet_id)

        if route and len(route) >= 2:
            next_hop = route[1]
            address = self.discovery.peers.get(next_hop) if self.discovery else None

            if address is not None:
                return self._transmit(packet, address, next_hop, tag="TX")

            logger.warning(
                "[ROUTE] next hop %s towards %s is not discovered yet; flooding",
                next_hop,
                message.destination,
            )
        else:
            logger.info(
                "[ROUTE] no full route from %s to %s; flooding to neighbors",
                message.source,
                message.destination,
            )

        sent_any = self._flood(packet, exclude_address=None)

        if not sent_any:
            self.stats["route_failures"] += 1
            logger.warning(
                "[ROUTE] no route and no reachable neighbors; "
                "packet %s not sent",
                packet.packet_id[:8],
            )

        return sent_any

    def _transmit(
        self,
        packet: Packet,
        address: RelayAddress,
        next_hop: str,
        tag: str = "TX",
    ) -> bool:
        sent = self.transport.send_to(
            packet.to_json().encode("utf-8"),
            address,
        )

        if sent:
            self.stats["tx_packets"] += 1
            logger.info(
                "[%s] packet %s %s -> %s via %s (ttl=%d)",
                tag,
                packet.packet_id[:8],
                packet.source,
                packet.destination,
                next_hop,
                packet.ttl,
            )

        return sent

    def _flood(self, packet: Packet, exclude_address: Optional[RelayAddress]) -> bool:
        """
        Send the packet to every direct neighbor with a known
        address, except the one it came from.

        Returns True when at least one copy went out.
        """
        sent_any = False

        for neighbor_id, address in self._neighbor_addresses():
            if exclude_address is not None and address == exclude_address:
                continue

            if self._transmit(packet, address, neighbor_id, tag="FLOOD"):
                sent_any = True

        return sent_any

    def _neighbor_addresses(self) -> List[Tuple[str, RelayAddress]]:
        """Direct topology neighbors with discovered socket addresses."""
        result: List[Tuple[str, RelayAddress]] = []

        if self.router is None or self.discovery is None:
            return result

        try:
            neighbors = self.router.topology.neighbors(self.node_id)
        except AttributeError:
            return result

        for neighbor_id in neighbors:
            address = self.discovery.peers.get(neighbor_id)

            if address is not None:
                result.append((neighbor_id, address))

        return result

    # ------------------------------------------------------------------
    # Receiving / forwarding
    # ------------------------------------------------------------------

    async def handle_packet(self, packet: Packet, addr: RelayAddress) -> None:
        """
        Process one validated packet.

        Order matters (see project requirements):

        1. duplicate detection
        2. liveness bookkeeping for the sender
        3. deliver locally or forward
        """
        self.stats["rx_packets"] += 1

        if self.duplicates.check_and_mark(packet.packet_id):
            self.stats["duplicates_dropped"] += 1
            logger.info(
                "[DUPLICATE] packet %s dropped", packet.packet_id[:8]
            )
            return

        self.discovery.record_heartbeat(packet.source)

        if packet.packet_type == PACKET_TYPE_ACK:
            if packet.destination == self.node_id:
                self._handle_ack(packet)
            else:
                # ACKs for other nodes' messages keep hopping back
                # along the recorded path towards the original source.
                self._forward_ack(packet)
            return

        if packet.packet_type == PACKET_TYPE_DATA:
            if packet.destination == self.node_id:
                self._deliver(packet)
            else:
                self._forward(packet)

    # ------------------------------------------------------------------
    # Local delivery
    # ------------------------------------------------------------------

    def _deliver(self, packet: Packet) -> None:
        message_id = _extract_message_id(packet.payload)

        if message_id and message_id in self._delivered_message_ids:
            # Retransmission after a lost ACK: re-ACK so the source
            # stops retrying, but do not deliver twice.
            logger.info(
                "[DUPLICATE] message %s already delivered; re-ACK",
                message_id[:8],
            )
            self._send_ack(packet)
            return

        text = _extract_text(packet.payload)

        self.inbox.append(
            {
                "message_id": _extract_message_id(packet.payload),
                "packet_id": packet.packet_id,
                "source": packet.source,
                "destination": packet.destination,
                "text": text,
                "hop_count": packet.hop_count,
                "received_at": time(),
            }
        )

        self.stats["delivered_packets"] += 1

        if message_id:
            self._delivered_message_ids.add(message_id)

            if len(self._delivered_message_ids) > 1000:
                self._delivered_message_ids.clear()

        logger.info(
            "[DELIVERED] from %s: %s (hops=%d)",
            packet.source,
            text,
            packet.hop_count,
        )

        self._send_ack(packet)

    def _record_hop(self, packet: Packet) -> None:
        """Append this node to the packet's recorded path (once)."""
        if isinstance(packet.payload, dict):
            via = packet.payload.setdefault("via", [])

            if isinstance(via, list) and self.node_id not in via:
                via.append(self.node_id)

    def _send_ack(self, packet: Packet) -> None:
        """
        ACK the original source along the reverse of the path the
        DATA packet took. Falls back to BFS routing, then to
        flooding when the recorded path is unusable.
        """
        message_id = _extract_message_id(packet.payload)

        # Path the DATA packet travelled (excluding the source),
        # ending at this node.
        via = (
            packet.payload.get("via")
            if isinstance(packet.payload, dict)
            else None
        )

        ack_path: Optional[List[str]] = None
        next_hop: Optional[str] = None

        if isinstance(via, list) and via:
            # ACK journey: this node -> reverse of the DATA path -> source.
            ack_path = (
                [self.node_id]
                + [str(node) for node in reversed(via)]
                + [packet.source]
            )

            if len(ack_path) >= 2:
                next_hop = ack_path[1]

        address = (
            self.discovery.peers.get(next_hop)
            if next_hop and self.discovery
            else None
        )

        if address is None:
            address = self.next_hop_address(packet.source)

        if address is None:
            logger.warning(
                "[ROUTE] cannot ACK %s: no route back to source",
                packet.source,
            )
            self.stats["route_failures"] += 1
            return

        ack = Packet(
            source=self.node_id,
            destination=packet.source,
            payload={
                "kind": "ACK",
                "ack_for": packet.packet_id,
                "message_id": message_id,
                "ack_path": ack_path,
            },
            ttl=DEFAULT_PACKET_TTL,
            packet_type=PACKET_TYPE_ACK,
        )

        sent = self.transport.send_to(ack.to_json().encode("utf-8"), address)

        if sent:
            self.stats["tx_packets"] += 1
            logger.info(
                "[TX] ACK %s for packet %s -> %s via %s",
                ack.packet_id[:8],
                packet.packet_id[:8],
                packet.source,
                next_hop or address[0],
            )

    def _forward_ack(self, packet: Packet) -> None:
        """
        Relay an ACK one hop closer to the original source using the
        ack_path recorded in its payload; BFS/flooding as fallback.
        """
        packet.decrement_ttl()

        if packet.is_expired():
            self.stats["expired_dropped"] += 1
            logger.warning(
                "[TTL] ACK %s expired at %s",
                packet.packet_id[:8],
                self.node_id,
            )
            return

        next_hop: Optional[str] = None

        if isinstance(packet.payload, dict):
            path = packet.payload.get("ack_path")

            if isinstance(path, list):
                ids = [str(node) for node in path]

                # Trim everything up to and including this node.
                if self.node_id in ids:
                    ids = ids[ids.index(self.node_id) + 1 :]

                packet.payload["ack_path"] = ids

                if ids:
                    next_hop = ids[0]

        address = (
            self.discovery.peers.get(next_hop)
            if next_hop and self.discovery
            else None
        )

        if address is None:
            address = self.next_hop_address(packet.destination)

        if address is not None:
            if self._transmit(
                packet,
                address,
                next_hop or packet.destination,
                tag="ACK-FWD",
            ):
                self.stats["forwarded_packets"] += 1
            return

        if self._flood(packet, exclude_address=None):
            self.stats["forwarded_packets"] += 1
        else:
            self.stats["route_failures"] += 1
            logger.warning(
                "[ROUTE] cannot forward ACK %s towards %s",
                packet.packet_id[:8],
                packet.destination,
            )

    def _handle_ack(self, packet: Packet) -> None:
        message_id = _extract_message_id(packet.payload)

        logger.info(
            "[ACK] packet %s delivered to %s",
            (message_id or packet.payload.get("ack_for", "?"))[:8]
            if isinstance(packet.payload, dict)
            else "?",
            packet.source,
        )

        if self.delivery_manager is not None and message_id:
            acknowledged = self.delivery_manager.acknowledge(message_id)

            if acknowledged:
                logger.info("[DELIVERED] message %s confirmed by ACK", message_id[:8])

    # ------------------------------------------------------------------
    # Multi-hop forwarding
    # ------------------------------------------------------------------

    def _forward(self, packet: Packet) -> None:
        # Record this node on the DATA path so the destination can
        # send its ACK back along the reverse route.
        self._record_hop(packet)

        packet.decrement_ttl()

        if packet.is_expired():
            self.stats["expired_dropped"] += 1
            logger.warning(
                "[TTL] packet %s expired at %s (hop_count=%d)",
                packet.packet_id[:8],
                self.node_id,
                packet.hop_count,
            )
            return

        route = self.find_route(self.node_id, packet.destination)

        if route and len(route) >= 2:
            next_hop = route[1]
            address = self.discovery.peers.get(next_hop) if self.discovery else None

            if address is not None:
                sent = self._transmit(packet, address, next_hop, tag="FORWARD")

                if sent:
                    self.stats["forwarded_packets"] += 1
                    logger.info(
                        "[ROUTE] %s", " -> ".join(route)
                    )
                return

            logger.warning(
                "[ROUTE] next hop %s not discovered; flooding packet %s",
                next_hop,
                packet.packet_id[:8],
            )
        else:
            logger.info(
                "[ROUTE] no route from %s towards %s; flooding packet %s",
                self.node_id,
                packet.destination,
                packet.packet_id[:8],
            )

        # Unicast routing failed: flood so the packet can still find
        # its way hop by hop. TTL + duplicate detection keep this
        # bounded.
        if self._flood(packet, exclude_address=None):
            self.stats["forwarded_packets"] += 1
        else:
            self.stats["route_failures"] += 1
            logger.warning(
                "[ROUTE] no reachable neighbors; packet %s dropped",
                packet.packet_id[:8],
            )


class RelayTransportAdapter(MessageTransport):
    """
    Exposes PacketRelay through the existing MessageTransport
    protocol so the existing DeliveryManager can use the real
    network without modification.
    """

    def __init__(self, relay: PacketRelay):
        self.relay = relay

    def find_route(self, source: str, destination: str) -> Optional[List[str]]:
        """
        Best-effort route for the existing DeliveryManager.

        The DeliveryManager only calls send() when find_route()
        returns something, so when BFS has no full path yet this
        returns a first-hop route (self -> any reachable neighbor).
        The actual delivery decision is then made hop by hop at the
        network layer (unicast when the route is known, flooding
        otherwise), and if the destination truly cannot be reached
        the packet dies by TTL without ever being stored at the
        destination.
        """
        route = self.relay.find_route(source, destination)

        if route:
            return route

        neighbors = self.relay.reachable_neighbor_ids()

        if neighbors:
            return [source, neighbors[0]]

        return None

    def send(self, message: Message, route: List[str]) -> bool:
        return self.relay.send_message(message, route)


def _extract_text(payload: Any) -> str:
    if isinstance(payload, dict):
        return str(payload.get("text", ""))
    return str(payload)


def _extract_message_id(payload: Any) -> str:
    if isinstance(payload, dict):
        value = payload.get("message_id")
        return str(value) if value else ""
    return ""
