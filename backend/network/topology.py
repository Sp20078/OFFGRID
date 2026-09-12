from typing import Dict, List, Set


class NetworkTopology:
    def __init__(self):
        # Each node maps to a set of directly connected neighbors.
        self.connections: Dict[str, Set[str]] = {}

    def add_node(self, node_id: str):
        """Add a node to the topology."""
        if node_id not in self.connections:
            self.connections[node_id] = set()

    def remove_node(self, node_id: str):
        """Remove a node and all connections to it."""
        if node_id not in self.connections:
            return

        self.connections.pop(node_id)

        for neighbors in self.connections.values():
            neighbors.discard(node_id)

    def connect(self, node_a: str, node_b: str):
        """Create a two-way connection between two nodes."""
        self.add_node(node_a)
        self.add_node(node_b)

        self.connections[node_a].add(node_b)
        self.connections[node_b].add(node_a)

    def disconnect(self, node_a: str, node_b: str):
        """Remove a two-way connection between two nodes."""
        if node_a in self.connections:
            self.connections[node_a].discard(node_b)

        if node_b in self.connections:
            self.connections[node_b].discard(node_a)

    def neighbors(self, node_id: str) -> List[str]:
        """Return directly connected neighbors."""
        return sorted(self.connections.get(node_id, set()))

    def has_node(self, node_id: str) -> bool:
        """Check whether a node exists."""
        return node_id in self.connections

    def has_connection(self, node_a: str, node_b: str) -> bool:
        """Check whether two nodes are directly connected."""
        return (
            node_a in self.connections
            and node_b in self.connections[node_a]
        )

    def node_count(self) -> int:
        """Return the number of nodes."""
        return len(self.connections)

    def connection_count(self) -> int:
        """Return the number of unique connections."""
        total = sum(len(neighbors) for neighbors in self.connections.values())
        return total // 2

    def get_graph(self) -> Dict[str, List[str]]:
        """Return the topology as a JSON-friendly dictionary."""
        return {
            node_id: sorted(neighbors)
            for node_id, neighbors in self.connections.items()
        }