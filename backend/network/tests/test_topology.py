from backend.network.topology import NetworkTopology


def test_add_nodes():
    topology = NetworkTopology()

    topology.add_node("A")
    topology.add_node("B")

    assert topology.has_node("A")
    assert topology.has_node("B")
    assert topology.node_count() == 2


def test_connect_nodes():
    topology = NetworkTopology()

    topology.connect("A", "B")

    assert topology.has_connection("A", "B")
    assert topology.has_connection("B", "A")
    assert topology.neighbors("A") == ["B"]
    assert topology.neighbors("B") == ["A"]


def test_disconnect_nodes():
    topology = NetworkTopology()

    topology.connect("A", "B")
    topology.disconnect("A", "B")

    assert not topology.has_connection("A", "B")
    assert not topology.has_connection("B", "A")


def test_remove_node():
    topology = NetworkTopology()

    topology.connect("A", "B")
    topology.connect("B", "C")

    topology.remove_node("B")

    assert not topology.has_node("B")
    assert topology.neighbors("A") == []
    assert topology.neighbors("C") == []


def test_offgrid_demo_topology():
    topology = NetworkTopology()

    topology.connect("A", "B")
    topology.connect("B", "C")
    topology.connect("C", "D")
    topology.connect("D", "E")

    assert topology.node_count() == 5
    assert topology.connection_count() == 4

    assert topology.neighbors("A") == ["B"]
    assert topology.neighbors("B") == ["A", "C"]
    assert topology.neighbors("C") == ["B", "D"]
    assert topology.neighbors("D") == ["C", "E"]
    assert topology.neighbors("E") == ["D"]