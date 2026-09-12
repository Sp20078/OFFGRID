from time import time

from .registry import NodeRegistry


class HeartbeatManager:
    def __init__(self, registry: NodeRegistry, timeout: float = 5.0):
        self.registry = registry
        self.timeout = timeout

    def receive_heartbeat(self, node_id: str):
        """Record that a node is alive."""
        self.registry.mark_online(node_id)

    def check_node(self, node_id: str) -> bool:
        """
        Check whether a node has responded recently.

        Returns True when the node is considered alive.
        """
        node = self.registry.get(node_id)

        if node is None:
            return False

        elapsed = time() - node.last_seen

        if elapsed > self.timeout:
            node.mark_offline()
            return False

        return True

    def check_all(self):
        """Check all registered nodes and mark stale nodes offline."""
        for node in self.registry.all_nodes():
            self.check_node(node.node_id)