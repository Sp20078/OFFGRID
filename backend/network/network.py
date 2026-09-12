from typing import List, Optional

from .node import Node
from .packet import Packet
from .registry import NodeRegistry
from .router import Router
from .topology import NetworkTopology


class NetworkEngine:
    """
    Coordinates the OFFGRID network core.

    Current implementation:
    - Finds routes using Router.
    - Validates every hop.
    - Simulates packet forwarding in memory.
    - Exposes send_message() for the messaging layer.

    Later, the forwarding part can be connected to UDP transport.
    """

    def __init__(
        self,
        node: Node,
        registry: NodeRegistry,
        topology: NetworkTopology,
        router: Router,
    ):
        self.node = node
        self.registry = registry
        self.topology = topology
        self.router = router

        self.forwarded_packets = 0
        self.delivered_packets = 0

    def find_route(
        self,
        source: str,
        destination: str,
    ) -> Optional[List[str]]:
        return self.router.find_route(
            source,
            destination,
        )

    def send_message(
        self,
        message,
        route: List[str],
    ) -> bool:
        """
        Convert a messaging Message into a network Packet
        and forward it through the supplied route.
        """

        if not route:
            return False

        if route[0] != message.source:
            return False

        if route[-1] != message.destination:
            return False

        packet = Packet(
            source=message.source,
            destination=message.destination,
            payload=message.payload,
            ttl=message.ttl,
        )

        return self.send_packet(packet, route)

    def send_packet(
        self,
        packet: Packet,
        route: List[str],
    ) -> bool:
        """
        Forward a packet through every node in the route.

        This is currently an in-memory transport.
        """

        if not route:
            return False

        if route[0] != packet.source:
            return False

        if route[-1] != packet.destination:
            return False

        # The source must exist and be online.
        source_node = self.registry.get(packet.source)

        if source_node is None:
            return False

        if not source_node.is_online():
            return False

        # Walk through every next hop.
        for node_id in route[1:]:
            node = self.registry.get(node_id)

            if node is None:
                return False

            if not node.is_online():
                return False

            packet.decrement_ttl()

            if packet.is_expired():
                return False

            self.forwarded_packets += 1

        self.delivered_packets += 1

        return True

    def get_metrics(self):
        return {
            "forwarded_packets": self.forwarded_packets,
            "delivered_packets": self.delivered_packets,
        }