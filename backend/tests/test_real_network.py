"""
Unit and integration tests for REAL LAN MODE.

Covers the requirement checklist: discovery parsing/registration,
packet (de)serialization, TTL, duplicates, heartbeats, route
selection, store-and-forward, ACK handling, and true multi-hop
forwarding over real localhost UDP sockets (no mocks for I/O).

All UDP tests bind to port 0 (ephemeral) so they never conflict
with developer machines.
"""

import asyncio
import json
from time import time

import pytest

from backend.messaging.delivery import DeliveryManager
from backend.messaging.message import Message, MessageStatus
from backend.network.node import Node
from backend.network.packet import KNOWN_PACKET_TYPES, Packet
from backend.network.registry import NodeRegistry
from backend.network.router import Router
from backend.network.topology import NetworkTopology
from backend.node_runtime.discovery import DiscoveryService
from backend.node_runtime.real_node import RealNode
from backend.node_runtime.relay import PacketRelay
from backend.node_runtime.udp_transport import UdpTransport


# ======================================================================
# Packet serialization / validation
# ======================================================================


def test_packet_serialization_round_trip():
    packet = Packet(
        source="NODE_A",
        destination="NODE_B",
        payload="Hello",
        ttl=10,
    )

    restored = Packet.from_json(packet.to_json())

    assert restored.packet_id == packet.packet_id
    assert restored.source == "NODE_A"
    assert restored.destination == "NODE_B"
    assert restored.payload == "Hello"
    assert restored.ttl == 10
    assert restored.hop_count == 0


def test_packet_deserialization_defaults():
    packet = Packet.from_dict(
        {
            "packet_id": "abc",
            "source": "NODE_A",
            "destination": "NODE_B",
            "payload": {"text": "hi"},
            "ttl": 5,
        }
    )

    assert packet.packet_type == "DATA"
    assert packet.hop_count == 0
    assert packet.payload["text"] == "hi"


def test_packet_rejects_unknown_packet_type():
    with pytest.raises(ValueError):
        Packet.from_dict(
            {
                "packet_id": "abc",
                "source": "NODE_A",
                "destination": "NODE_B",
                "payload": "x",
                "ttl": 5,
                "packet_type": "NUKE",
            }
        )


def test_packet_rejects_missing_fields():
    with pytest.raises(ValueError):
        Packet.from_dict({"source": "NODE_A"})


def test_packet_rejects_invalid_ttl():
    with pytest.raises(ValueError):
        Packet.from_dict(
            {
                "packet_id": "abc",
                "source": "NODE_A",
                "destination": "NODE_B",
                "payload": "x",
                "ttl": -3,
            }
        )


def test_known_packet_types_include_control_types():
    assert {"DATA", "ACK", "HEARTBEAT", "DISCOVERY"} == KNOWN_PACKET_TYPES


def test_ttl_decrement_and_expiry():
    packet = Packet(source="A", destination="E", payload="x", ttl=2)

    packet.decrement_ttl()
    assert packet.ttl == 1 and packet.hop_count == 1
    assert not packet.is_expired()

    packet.decrement_ttl()
    assert packet.ttl == 0 and packet.is_expired()


# ======================================================================
# Discovery parsing / registration
# ======================================================================


def _make_discovery(node_id="NODE_A", udp_port=9001) -> DiscoveryService:
    registry = NodeRegistry()
    topology = NetworkTopology()

    discovery = DiscoveryService(
        transport=None,
        node_id=node_id,
        udp_port=udp_port,
        api_port=8001,
        registry=registry,
        topology=topology,
    )

    registry.add(Node(node_id=node_id, address="127.0.0.1", port=udp_port))
    topology.add_node(node_id)

    return discovery


def _announcement(node_id: str, ip: str, port: int) -> bytes:
    return json.dumps(
        {
            "packet_type": "DISCOVERY",
            "node_id": node_id,
            "ip": ip,
            "udp_port": port,
            "timestamp": time(),
            "protocol_version": 1,
        }
    ).encode()


def test_discovery_parses_valid_announcement():
    discovery = _make_discovery()

    asyncio.run(
        discovery.handle_datagram(
            _announcement("NODE_B", "192.168.1.102", 9002),
            ("192.168.1.102", 9002),
        )
    )

    node = discovery.registry.get("NODE_B")

    assert node is not None
    assert node.address == "192.168.1.102"
    assert node.port == 9002
    assert node.is_online()
    assert discovery.peers["NODE_B"] == ("192.168.1.102", 9002)
    assert discovery.topology.has_connection("NODE_A", "NODE_B")


def test_discovery_ignores_own_announcement():
    discovery = _make_discovery()

    asyncio.run(
        discovery.handle_datagram(
            _announcement("NODE_A", "127.0.0.1", 9001),
            ("127.0.0.1", 9001),
        )
    )

    assert discovery.registry.count() == 1
    assert "NODE_A" not in discovery.peers


def test_discovery_rejects_malformed_json():
    discovery = _make_discovery()

    asyncio.run(discovery.handle_datagram(b"not json", ("10.0.0.9", 1234)))

    assert discovery.registry.count() == 1


def test_discovery_rejects_unknown_packet_type():
    discovery = _make_discovery()

    asyncio.run(
        discovery.handle_datagram(
            json.dumps({"packet_type": "MYSTERY", "node_id": "X"}).encode(),
            ("10.0.0.9", 1234),
        )
    )

    assert discovery.registry.count() == 1


def test_discovery_rejects_wrong_protocol_version():
    discovery = _make_discovery()

    asyncio.run(
        discovery.handle_datagram(
            json.dumps(
                {
                    "packet_type": "DISCOVERY",
                    "node_id": "NODE_B",
                    "protocol_version": 99,
                }
            ).encode(),
            ("10.0.0.9", 1234),
        )
    )

    assert "NODE_B" not in discovery.peers


def test_discovery_rejects_invalid_port():
    discovery = _make_discovery()

    asyncio.run(
        discovery.handle_datagram(
            json.dumps(
                {
                    "packet_type": "DISCOVERY",
                    "node_id": "NODE_B",
                    "ip": "192.168.1.102",
                    "udp_port": 99999,
                    "protocol_version": 1,
                }
            ).encode(),
            ("192.168.1.102", 9002),
        )
    )

    assert "NODE_B" not in discovery.peers


def test_discovery_refreshes_existing_peer():
    discovery = _make_discovery()

    asyncio.run(
        discovery.handle_datagram(
            _announcement("NODE_B", "192.168.1.102", 9002),
            ("192.168.1.102", 9002),
        )
    )

    node = discovery.registry.get("NODE_B")
    node.last_seen = time() - 100

    asyncio.run(
        discovery.handle_datagram(
            _announcement("NODE_B", "192.168.1.102", 9002),
            ("192.168.1.102", 9002),
        )
    )

    assert node.is_online()


def test_heartbeat_expiry_marks_offline_and_disconnects():
    discovery = _make_discovery()
    discovery.register_peer("NODE_B", "192.168.1.102", 9002)

    node_b = discovery.registry.get("NODE_B")
    node_b.last_seen = time() - 100

    went_offline = discovery.expire_stale_peers()

    assert went_offline == ["NODE_B"]
    assert not node_b.is_online()
    assert not discovery.topology.has_connection("NODE_A", "NODE_B")
    # Address is kept so unicast announcements keep flowing to the
    # stale address and the pair re-registers when the peer returns.
    assert discovery.peers["NODE_B"] == ("192.168.1.102", 9002)


def test_expired_peer_reRegisters_on_next_announcement():
    discovery = _make_discovery()
    discovery.register_peer("NODE_B", "192.168.1.102", 9002)

    node_b = discovery.registry.get("NODE_B")
    node_b.last_seen = time() - 100

    assert discovery.expire_stale_peers() == ["NODE_B"]
    assert not node_b.is_online()

    # Peer laptop comes back: one announcement heals the pair.
    asyncio.run(
        discovery.handle_datagram(
            _announcement("NODE_B", "192.168.1.102", 9002),
            ("192.168.1.102", 9002),
        )
    )

    assert node_b.is_online()
    assert discovery.topology.has_connection("NODE_A", "NODE_B")


def test_local_ip_returns_string():
    ip = DiscoveryService.local_ip()

    assert isinstance(ip, str)
    assert ip


# ======================================================================
# Route selection (existing BFS Router + registry)
# ======================================================================


def _chain_topology(registry) -> tuple[NetworkTopology, Router]:
    topology = NetworkTopology()

    for node_id in ["NODE_A", "NODE_B", "NODE_C", "NODE_D", "NODE_E"]:
        topology.add_node(node_id)

    for a, b in [
        ("NODE_A", "NODE_B"),
        ("NODE_B", "NODE_C"),
        ("NODE_C", "NODE_D"),
        ("NODE_D", "NODE_E"),
    ]:
        topology.connect(a, b)

    return topology, Router(topology=topology, registry=registry)


def _registry() -> NodeRegistry:
    registry = NodeRegistry()

    for node_id in ["NODE_A", "NODE_B", "NODE_C", "NODE_D", "NODE_E"]:
        registry.add(Node(node_id=node_id, address="127.0.0.1", port=9001))

    return registry


def test_route_selection_linear_chain():
    _, router = _chain_topology(_registry())

    assert router.find_route("NODE_A", "NODE_E") == [
        "NODE_A",
        "NODE_B",
        "NODE_C",
        "NODE_D",
        "NODE_E",
    ]


def test_route_avoids_offline_node():
    registry = _registry()
    _, router = _chain_topology(registry)

    registry.get("NODE_C").mark_offline()

    # Pure chain: no alternate path exists.
    assert router.find_route("NODE_A", "NODE_E") is None


def test_route_reroutes_through_backup_link():
    registry = _registry()
    topology, router = _chain_topology(registry)

    # Alternate path B - D (the demo topology's backup edge).
    topology.connect("NODE_B", "NODE_D")

    registry.get("NODE_C").mark_offline()

    assert router.find_route("NODE_A", "NODE_E") == [
        "NODE_A",
        "NODE_B",
        "NODE_D",
        "NODE_E",
    ]


# ======================================================================
# Real UDP socket send/receive (no mocks)
# ======================================================================


def test_udp_transport_real_send_receive():
    """A real datagram crosses a real socket pair on localhost."""

    async def scenario():
        received: list[bytes] = []
        got_event = asyncio.Event()

        async def handler(data, addr):
            received.append(data)
            got_event.set()

        receiver = UdpTransport("127.0.0.1", 0, handler)
        await receiver.start()

        sender = UdpTransport("127.0.0.1", 0, handler)
        await sender.start()

        sent = sender.send_to(b"ping-offgrid", ("127.0.0.1", receiver.port))

        await asyncio.wait_for(got_event.wait(), timeout=3)

        await sender.stop()
        await receiver.stop()

        assert sent is True
        assert received and received[0] == b"ping-offgrid"

    asyncio.run(scenario())


def test_udp_transport_rejects_oversized_outgoing():
    async def scenario():
        transport = UdpTransport("127.0.0.1", 0, None)
        await transport.start()

        sent = transport.send_to(b"x" * 70_000, ("127.0.0.1", 9000))

        await transport.stop()

        assert sent is False

    asyncio.run(scenario())


# ======================================================================
# Multi-hop forwarding over REAL localhost UDP sockets
# ======================================================================


class _NodeHarness:
    """
    Minimal wiring of UdpTransport + DiscoveryService + PacketRelay
    for integration tests (bypasses RealNode's API/background loops).
    """

    def __init__(self, node_id: str):
        self.node_id = node_id

        self.registry = NodeRegistry()
        self.topology = NetworkTopology()
        self.router = Router(topology=self.topology, registry=self.registry)

        self.received: list[Packet] = []

        async def handler(data, addr):
            try:
                message = json.loads(data.decode())
            except (ValueError, UnicodeDecodeError):
                return

            if message.get("packet_type") == "DISCOVERY":
                await self.discovery.handle_datagram(data, addr)
                return

            try:
                packet = Packet.from_dict(message)
            except ValueError:
                return

            self.received.append(packet)

            await self.relay.handle_packet(packet, addr)

        self.transport = UdpTransport("127.0.0.1", 0, handler)

        self.discovery = DiscoveryService(
            transport=self.transport,
            node_id=node_id,
            udp_port=0,
            api_port=None,
            registry=self.registry,
            topology=self.topology,
        )

        self.registry.add(Node(node_id=node_id, address="127.0.0.1", port=0))
        self.topology.add_node(node_id)

        self.relay = PacketRelay(
            node_id=node_id,
            transport=self.transport,
            discovery=self.discovery,
            router=self.router,
        )

    async def start(self):
        await self.transport.start()

    async def stop(self):
        await self.transport.stop()

    def address(self) -> tuple[str, int]:
        return ("127.0.0.1", self.transport.port)

    def know_peer(self, other: "_NodeHarness"):
        self.discovery.register_peer(other.node_id, "127.0.0.1", other.address()[1])


async def _wait_until(predicate, timeout: float = 5.0):
    async def _wait():
        while not predicate():
            await asyncio.sleep(0.02)

    return await asyncio.wait_for(_wait(), timeout=timeout)


def test_two_node_delivery_over_real_udp():
    """NODE_A -> NODE_B directly over real sockets."""

    async def scenario():
        node_a = _NodeHarness("NODE_A")
        node_b = _NodeHarness("NODE_B")

        await node_a.start()
        await node_b.start()

        node_a.know_peer(node_b)
        node_b.know_peer(node_a)

        message = Message.create(
            source="NODE_A",
            destination="NODE_B",
            payload="Hello from Laptop 1",
        )

        assert node_a.relay.send_message(message) is True

        await _wait_until(lambda: len(node_b.received) >= 1)

        # Let the ACK travel back before tearing down.
        await _wait_until(
            lambda: any(p.packet_type == "ACK" for p in node_a.received),
        )

        await node_a.stop()
        await node_b.stop()

        packet = node_b.received[0]

        assert packet.source == "NODE_A"
        assert packet.destination == "NODE_B"
        assert packet.payload["text"] == "Hello from Laptop 1"

        assert node_b.relay.stats["delivered_packets"] == 1
        assert node_b.relay.inbox[0]["text"] == "Hello from Laptop 1"
        assert node_b.relay.inbox[0]["source"] == "NODE_A"

    asyncio.run(scenario())


def test_three_node_multihop_over_real_udp():
    """NODE_A -> NODE_B -> NODE_C: B physically forwards the packet."""

    async def scenario():
        node_a = _NodeHarness("NODE_A")
        node_b = _NodeHarness("NODE_B")
        node_c = _NodeHarness("NODE_C")

        for harness in (node_a, node_b, node_c):
            await harness.start()

        node_a.know_peer(node_b)
        node_b.know_peer(node_a)
        node_b.know_peer(node_c)
        node_c.know_peer(node_b)

        # B is NOT the destination: it must forward through its socket.
        message = Message.create(
            source="NODE_A",
            destination="NODE_C",
            payload="multi-hop hello",
        )

        assert node_a.relay.send_message(message) is True

        await _wait_until(lambda: len(node_c.received) >= 1)

        # ACK travels back C -> B -> A over real sockets.
        await _wait_until(
            lambda: any(p.packet_type == "ACK" for p in node_a.received),
        )

        await node_a.stop()
        await node_b.stop()
        await node_c.stop()

        assert node_c.received[0].payload["text"] == "multi-hop hello"
        assert node_c.received[0].hop_count == 1

        # B must have actually forwarded (not delivered) — both the
        # DATA packet and the ACK on the way back.
        assert node_b.relay.stats["forwarded_packets"] >= 1
        assert node_b.relay.stats["delivered_packets"] == 0

        # B relayed the ACK back towards A.
        assert any(p.packet_type == "ACK" for p in node_a.received)

    asyncio.run(scenario())


def test_ttl_zero_packet_is_dropped_not_forwarded():
    async def scenario():
        node_a = _NodeHarness("NODE_A")
        node_b = _NodeHarness("NODE_B")
        node_c = _NodeHarness("NODE_C")

        for harness in (node_a, node_b, node_c):
            await harness.start()

        node_a.know_peer(node_b)
        node_b.know_peer(node_a)
        node_b.know_peer(node_c)
        node_c.know_peer(node_b)

        # ttl=1: B decrements to 0 -> expired, C never sees it.
        message = Message.create(
            source="NODE_A",
            destination="NODE_C",
            payload="dies at B",
            ttl=1,
        )

        node_a.relay.send_message(message)

        await asyncio.sleep(0.4)

        await node_a.stop()
        await node_b.stop()
        await node_c.stop()

        assert node_c.relay.stats["rx_packets"] == 0
        assert node_b.relay.stats["expired_dropped"] == 1

    asyncio.run(scenario())


def test_duplicate_packet_is_dropped():
    async def scenario():
        node_a = _NodeHarness("NODE_A")
        node_b = _NodeHarness("NODE_B")

        await node_a.start()
        await node_b.start()

        node_a.know_peer(node_b)
        node_b.know_peer(node_a)

        packet = Packet(
            source="NODE_A",
            destination="NODE_B",
            payload={"kind": "MESSAGE", "message_id": "m-1", "text": "once"},
            ttl=5,
        )

        raw = packet.to_json().encode()

        node_a.transport.send_to(raw, node_b.address())
        node_a.transport.send_to(raw, node_b.address())

        await asyncio.sleep(0.4)

        await node_a.stop()
        await node_b.stop()

        assert node_b.relay.stats["duplicates_dropped"] == 1
        assert node_b.relay.stats["delivered_packets"] == 1

    asyncio.run(scenario())


def test_relay_without_route_fails_cleanly():
    relay = PacketRelay(
        node_id="NODE_A",
        transport=None,
        discovery=None,
        router=None,
    )

    message = Message.create(
        source="NODE_A",
        destination="NODE_Z",
        payload="nowhere",
    )

    assert relay.send_message(message) is False
    assert relay.stats["route_failures"] == 1


# ======================================================================
# Store-and-forward + ACK (existing DeliveryManager)
# ======================================================================


class _RouteAwareTransport:
    """
    MessageTransport whose send() succeeds when the existing BFS
    Router finds a route; DeliveryManager queues otherwise.
    """

    def __init__(self, router: Router):
        self.router = router

    def find_route(self, source, destination):
        return self.router.find_route(source, destination)

    def send(self, message, route):
        return bool(route)


def test_store_and_forward_when_destination_offline():
    """
    NODE_E offline -> no route -> message stored as PENDING.
    When NODE_E returns, retry_pending delivers it.
    """
    registry = _registry()
    _, router = _chain_topology(registry)

    registry.get("NODE_E").mark_offline()

    manager = DeliveryManager(router=_RouteAwareTransport(router), max_retries=3)

    message = manager.create_message(
        source="NODE_A",
        destination="NODE_E",
        payload="stored msg",
    )

    assert manager.deliver(message) is False
    assert message.status == MessageStatus.PENDING
    assert manager.queue.size("NODE_E") == 1

    # NODE_E returns.
    registry.get("NODE_E").mark_seen()

    delivered = manager.retry_pending("NODE_E")

    assert delivered == [message.message_id]
    assert manager.queue.size("NODE_E") == 0


def test_ack_marks_message_delivered():
    registry = _registry()
    _, router = _chain_topology(registry)

    manager = DeliveryManager(router=_RouteAwareTransport(router), max_retries=3)

    message = manager.create_message(
        source="NODE_A",
        destination="NODE_E",
        payload="ack me",
    )

    assert manager.deliver(message) is True
    assert message.status == MessageStatus.FORWARDED

    assert manager.acknowledge(message.message_id) is True
    assert manager.store.get(message.message_id).status == MessageStatus.DELIVERED
    assert manager.queue.size() == 0


def test_retry_respects_max_retries():
    registry = _registry()
    _, router = _chain_topology(registry)

    registry.get("NODE_E").mark_offline()

    manager = DeliveryManager(router=_RouteAwareTransport(router), max_retries=2)

    message = manager.create_message(
        source="NODE_A",
        destination="NODE_E",
        payload="try me",
    )

    # deliver() queues without consuming retry budget; explicit
    # retries count against max_retries.
    manager.retry_message(message)
    manager.retry_message(message)

    assert manager.get_retry_count(message.message_id) == 2
    assert manager.retry_message(message) is False


# ======================================================================
# RealNode integration (full wiring, real sockets, no API server)
# ======================================================================


def _make_real_node(node_id: str) -> RealNode:
    return RealNode(
        node_id=node_id,
        udp_port=0,
        discovery_port=0,
        api_port=None,  # headless
        heartbeat_interval=0.2,
        heartbeat_timeout=1.5,
    )


def test_realnode_end_to_end_two_nodes():
    """
    Full RealNode wiring over real UDP: NODE_A sends, NODE_B's
    relay inbox holds the payload, NODE_A's DeliveryManager ends
    in DELIVERED after the real ACK round trip.
    """

    async def scenario():
        node_a = _make_real_node("NODE_A")
        node_b = _make_real_node("NODE_B")

        await node_a.start()
        await node_b.start()

        # Simulate discovery: each knows the other's real address.
        node_a.discovery.register_peer(
            "NODE_B", "127.0.0.1", node_b.udp_port_actual()
        )
        node_b.discovery.register_peer(
            "NODE_A", "127.0.0.1", node_a.udp_port_actual()
        )

        result = node_a.send_custom_message(
            destination="NODE_B", payload="Hello from Laptop 1"
        )

        assert result["status"] == "FORWARDED"

        async def _wait_delivered():
            while (
                node_a.delivery_manager.store.get(result["message_id"]).status
                != MessageStatus.DELIVERED
            ):
                await asyncio.sleep(0.02)

        await asyncio.wait_for(_wait_delivered(), timeout=5)

        await node_a.stop()
        await node_b.stop()

        assert node_b.relay.inbox[-1]["text"] == "Hello from Laptop 1"
        assert node_b.relay.inbox[-1]["source"] == "NODE_A"

    asyncio.run(scenario())


def test_realnode_end_to_end_multihop():
    """
    A -> B -> C over real sockets with the full RealNode stack,
    including the ACK travelling back C -> B -> A.
    """

    async def scenario():
        node_a = _make_real_node("NODE_A")
        node_b = _make_real_node("NODE_B")
        node_c = _make_real_node("NODE_C")

        await node_a.start()
        await node_b.start()
        await node_c.start()

        node_a.discovery.register_peer(
            "NODE_B", "127.0.0.1", node_b.udp_port_actual()
        )
        node_b.discovery.register_peer(
            "NODE_A", "127.0.0.1", node_a.udp_port_actual()
        )
        node_b.discovery.register_peer(
            "NODE_C", "127.0.0.1", node_c.udp_port_actual()
        )
        node_c.discovery.register_peer(
            "NODE_B", "127.0.0.1", node_b.udp_port_actual()
        )

        result = node_a.send_custom_message(
            destination="NODE_C", payload="hop hop"
        )

        assert result["status"] == "FORWARDED"

        async def _wait_delivered():
            while (
                node_a.delivery_manager.store.get(result["message_id"]).status
                != MessageStatus.DELIVERED
            ):
                await asyncio.sleep(0.02)

        await asyncio.wait_for(_wait_delivered(), timeout=5)

        await node_a.stop()
        await node_b.stop()
        await node_c.stop()

        assert node_c.relay.inbox[-1]["text"] == "hop hop"
        # B forwards the DATA packet AND the returning ACK.
        assert node_b.relay.stats["forwarded_packets"] == 2

    asyncio.run(scenario())


def test_realnode_store_and_forward_recovers_when_peer_returns():
    """
    B offline: message for B stays PENDING on A. B 'returns'
    (registers again), A's flush loop delivers it and B's inbox
    receives the text.
    """

    async def scenario():
        node_a = _make_real_node("NODE_A")
        node_b = _make_real_node("NODE_B")

        await node_a.start()

        # B is not running yet: A cannot route to it.
        result = node_a.send_custom_message(
            destination="NODE_B", payload="wait for me"
        )

        assert result["status"] == "PENDING"
        assert node_a.delivery_manager.queue.size("NODE_B") == 1

        # B comes online and discovers A.
        await node_b.start()
        node_a.discovery.register_peer(
            "NODE_B", "127.0.0.1", node_b.udp_port_actual()
        )

        async def _wait_inbox():
            while not node_b.relay.inbox:
                await asyncio.sleep(0.05)

        await asyncio.wait_for(_wait_inbox(), timeout=8)

        await node_a.stop()
        await node_b.stop()

        assert node_b.relay.inbox[-1]["text"] == "wait for me"

    asyncio.run(scenario())


def test_realnode_snapshot_shape_matches_dashboard():
    """
    The snapshot must satisfy the existing frontend MeshNode /
    MeshLink / NetworkMetrics shapes.
    """

    async def scenario():
        node = _make_real_node("NODE_A")
        await node.start()

        snap = node.snapshot()

        await node.stop()

        assert snap["mode"] == "real"
        assert snap["nodeId"] == "NODE_A"

        for field in (
            "nodes",
            "links",
            "activeRoute",
            "metrics",
            "logs",
            "internetOnline",
            "inbox",
            "pendingMessages",
        ):
            assert field in snap

        self_node = next(n for n in snap["nodes"] if n["id"] == "NODE_A")

        for field in (
            "id",
            "label",
            "status",
            "ip",
            "latencyMs",
            "storedPacketsCount",
            "x",
            "y",
            "neighbors",
            "lastSeenMs",
        ):
            assert field in self_node

        metrics = snap["metrics"]

        for field in (
            "totalNodes",
            "activeNodes",
            "activeLinksCount",
            "activePathHops",
            "internetAvailable",
            "storeAndForwardQueueSize",
            "avgMeshLatencyMs",
        ):
            assert field in metrics

        assert self_node["status"] == "ONLINE"
        assert metrics["activeNodes"] >= 1

    asyncio.run(scenario())


def test_realnode_rejects_send_to_unknown_destination():
    async def scenario():
        node = _make_real_node("NODE_A")
        await node.start()

        result = node.send_custom_message(
            destination="NODE_NOWHERE", payload="?"
        )

        await node.stop()

        assert result["status"] == "PENDING"
        assert node.delivery_manager.queue.size("NODE_NOWHERE") == 1

    asyncio.run(scenario())
