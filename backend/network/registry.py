from typing import Dict, List, Optional

from .node import Node, NodeStatus


class NodeRegistry:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}

    def add(self, node: Node):
        self.nodes[node.node_id] = node

    def remove(self, node_id: str):
        self.nodes.pop(node_id, None)

    def get(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def mark_online(self, node_id: str):
        node = self.get(node_id)

        if node:
            node.mark_seen()

    def mark_offline(self, node_id: str):
        node = self.get(node_id)

        if node:
            node.mark_offline()

    def online_nodes(self) -> List[Node]:
        return [
            node
            for node in self.nodes.values()
            if node.status == NodeStatus.ONLINE
        ]

    def all_nodes(self) -> List[Node]:
        return list(self.nodes.values())

    def contains(self, node_id: str):
        return node_id in self.nodes

    def count(self):
        return len(self.nodes)

    def online_count(self):
        return len(self.online_nodes())