from time import time

from backend.network.heartbeat import HeartbeatManager
from backend.network.node import Node
from backend.network.registry import NodeRegistry


def test_heartbeat_marks_node_online():
    registry = NodeRegistry()

    node = Node(
        node_id="A",
        address="127.0.0.1",
        port=5001,
    )

    registry.add(node)
    registry.mark_offline("A")

    heartbeat = HeartbeatManager(registry)

    heartbeat.receive_heartbeat("A")

    node_a = registry.get("A")

    assert node_a is not None
    assert node_a.is_online()


def test_old_heartbeat_marks_node_offline():
    registry = NodeRegistry()

    node = Node(
        node_id="A",
        address="127.0.0.1",
        port=5001,
    )

    registry.add(node)

    # Simulate an old heartbeat.
    node.last_seen = time() - 10

    heartbeat = HeartbeatManager(
        registry,
        timeout=5,
    )

    assert not heartbeat.check_node("A")
    assert not node.is_online()


def test_check_all_marks_stale_nodes_offline():
    registry = NodeRegistry()

    node_a = Node("A", "127.0.0.1", 5001)
    node_b = Node("B", "127.0.0.1", 5002)

    registry.add(node_a)
    registry.add(node_b)

    node_b.last_seen = time() - 10

    heartbeat = HeartbeatManager(
        registry,
        timeout=5,
    )

    heartbeat.check_all()

    assert node_a.is_online()
    assert not node_b.is_online()