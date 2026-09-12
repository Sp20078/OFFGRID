from backend.network.node import Node
from backend.network.network import NetworkEngine
from backend.network.registry import NodeRegistry
from backend.network.router import Router
from backend.network.topology import NetworkTopology
from backend.messaging.message import Message


def build_network():
    registry = NodeRegistry()
    topology = NetworkTopology()

    for node_id in ["A", "B", "C", "D", "E"]:
        registry.add(
            Node(
                node_id=node_id,
                address="127.0.0.1",
                port=5000 + ord(node_id),
            )
        )

    topology.connect("A", "B")
    topology.connect("B", "C")
    topology.connect("C", "D")
    topology.connect("D", "E")

    # Alternate route for failure recovery.
    topology.connect("B", "D")

    router = Router(
        topology=topology,
        registry=registry,
    )

    engine = NetworkEngine(
        node=registry.get("A"),
        registry=registry,
        topology=topology,
        router=router,
    )

    return engine, registry, topology


def test_message_travels_through_network():
    engine, _, _ = build_network()

    message = Message.create(
        source="A",
        destination="E",
        payload="Emergency evacuation",
    )

    route = engine.find_route("A", "E")

    assert route == ["A", "B", "D", "E"]

    assert engine.send_message(
        message,
        route,
    )

    metrics = engine.get_metrics()

    assert metrics["delivered_packets"] == 1
    assert metrics["forwarded_packets"] == 3


def test_message_fails_when_route_contains_offline_node():
    engine, registry, topology = build_network()

    # Remove alternate route so the only path uses C.
    topology.disconnect("B", "D")

    registry.mark_offline("C")

    message = Message.create(
        source="A",
        destination="E",
        payload="Test failure",
    )

    route = engine.find_route("A", "E")

    assert route is None
    assert not engine.send_message(
        message,
        ["A", "B", "C", "D", "E"],
    )


def test_message_reroutes_after_node_failure():
    engine, registry, topology = build_network()

    registry.mark_offline("C")

    message = Message.create(
        source="A",
        destination="E",
        payload="Reroute test",
    )

    route = engine.find_route("A", "E")

    assert route == ["A", "B", "D", "E"]

    assert engine.send_message(
        message,
        route,
    )