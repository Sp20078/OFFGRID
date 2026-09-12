from backend.network.router import Router
from backend.network.topology import NetworkTopology


def build_demo_topology():
    topology = NetworkTopology()

    topology.connect("A", "B")
    topology.connect("B", "C")
    topology.connect("C", "D")
    topology.connect("D", "E")

    return topology


def test_find_route():
    topology = build_demo_topology()
    router = Router(topology)

    route = router.find_route("A", "E")

    assert route == ["A", "B", "C", "D", "E"]


def test_find_route_reverse():
    topology = build_demo_topology()
    router = Router(topology)

    route = router.find_route("E", "A")

    assert route == ["E", "D", "C", "B", "A"]


def test_find_route_same_node():
    topology = build_demo_topology()
    router = Router(topology)

    assert router.find_route("A", "A") == ["A"]


def test_no_route():
    topology = NetworkTopology()

    topology.connect("A", "B")
    topology.connect("C", "D")

    router = Router(topology)

    assert router.find_route("A", "D") is None


def test_reroute_after_failure():
    topology = NetworkTopology()

    topology.connect("A", "B")
    topology.connect("B", "C")
    topology.connect("C", "D")
    topology.connect("D", "E")

    # Backup connection that becomes useful when C fails.
    topology.connect("B", "D")

    router = Router(topology)

    route_before = router.find_route("A", "E")
    assert route_before == ["A", "B", "D", "E"]

    topology.remove_node("C")

    route_after = router.find_route("A", "E")
    assert route_after == ["A", "B", "D", "E"]

def test_offline_node_is_ignored():
    topology = NetworkTopology()
    topology.connect("A", "B")
    topology.connect("B", "C")
    topology.connect("C", "D")
    topology.connect("D", "E")

    from backend.network.registry import NodeRegistry
    from backend.network.node import Node

    registry = NodeRegistry()

    for node_id in ["A", "B", "C", "D", "E"]:
        registry.add(
            Node(
                node_id=node_id,
                address="127.0.0.1",
                port=5000 + ord(node_id),
            )
        )

    router = Router(topology, registry)

    registry.mark_offline("C")

    assert router.find_route("A", "E") is None


def test_offline_node_can_be_bypassed():
    topology = NetworkTopology()

    topology.connect("A", "B")
    topology.connect("B", "C")
    topology.connect("C", "D")
    topology.connect("D", "E")
    topology.connect("B", "D")

    from backend.network.registry import NodeRegistry
    from backend.network.node import Node

    registry = NodeRegistry()

    for node_id in ["A", "B", "C", "D", "E"]:
        registry.add(
            Node(
                node_id=node_id,
                address="127.0.0.1",
                port=5000 + ord(node_id),
            )
        )

    router = Router(topology, registry)

    registry.mark_offline("C")

    assert router.find_route("A", "E") == ["A", "B", "D", "E"]