from collections import deque
from typing import List, Optional

from .registry import NodeRegistry
from .topology import NetworkTopology


class Router:
    def __init__(
        self,
        topology: NetworkTopology,
        registry: Optional[NodeRegistry] = None,
    ):
        self.topology = topology
        self.registry = registry

    def _is_available(self, node_id: str) -> bool:
        """Return whether a node can currently participate in routing."""

        if self.registry is None:
            return True

        node = self.registry.get(node_id)

        if node is None:
            return False

        return node.is_online()

    def find_route(
        self,
        source: str,
        destination: str,
    ) -> Optional[List[str]]:
        """
        Find the shortest route from source to destination,
        ignoring offline nodes.
        """

        if not self.topology.has_node(source):
            return None

        if not self.topology.has_node(destination):
            return None

        if not self._is_available(source):
            return None

        if not self._is_available(destination):
            return None

        if source == destination:
            return [source]

        queue = deque([[source]])
        visited = {source}

        while queue:
            path = queue.popleft()
            current = path[-1]

            for neighbor in self.topology.neighbors(current):
                if neighbor in visited:
                    continue

                if not self._is_available(neighbor):
                    continue

                new_path = path + [neighbor]

                if neighbor == destination:
                    return new_path

                visited.add(neighbor)
                queue.append(new_path)

        return None