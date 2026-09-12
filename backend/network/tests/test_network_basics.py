from backend.network.node import Node, NodeStatus
from backend.network.packet import Packet
from backend.network.registry import NodeRegistry


def test_node_creation():
    node = Node(
        node_id="A",
        address="127.0.0.1",
        port=5001
    )

    assert node.node_id == "A"
    assert node.address == "127.0.0.1"
    assert node.port == 5001
    assert node.status == NodeStatus.ONLINE
    assert node.is_online()


def test_node_offline_and_online():
    node = Node(
        node_id="A",
        address="127.0.0.1",
        port=5001
    )

    node.mark_offline()

    assert node.status == NodeStatus.OFFLINE
    assert not node.is_online()

    node.mark_seen()

    assert node.status == NodeStatus.ONLINE
    assert node.is_online()


def test_packet_ttl():
    packet = Packet(
        source="A",
        destination="E",
        payload="Hello",
        ttl=2
    )

    assert packet.ttl == 2
    assert packet.hop_count == 0

    packet.decrement_ttl()

    assert packet.ttl == 1
    assert packet.hop_count == 1

    packet.decrement_ttl()

    assert packet.ttl == 0
    assert packet.hop_count == 2
    assert packet.is_expired()


def test_registry():
    registry = NodeRegistry()

    node_a = Node("A", "127.0.0.1", 5001)
    node_b = Node("B", "127.0.0.1", 5002)

    registry.add(node_a)
    registry.add(node_b)

    assert registry.count() == 2
    assert registry.online_count() == 2

    registry.mark_offline("B")

    assert registry.count() == 2
    assert registry.online_count() == 1

    assert registry.get("A") == node_a
    assert registry.get("B") == node_b