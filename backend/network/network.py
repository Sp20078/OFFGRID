from typing import List, Optional

from .node import Node
from .packet import Packet
from .registry import NodeRegistry
from .router import Router
from .topology import NetworkTopology


class NetworkEngine:
    """
    Coordinates the OFFGRID network core.

    Responsibilities:
    - maintain local node information
    - find routes
    - forward packets
    - expose send_message() to the messaging layer
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

    def send_message(self, message, route: List[str]) -> bool:
        """
        Convert a messaging-layer message into a network packet
        and forward it along the supplied route.

        For now this is an in-memory transport.
        UDP transport will be added later.
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
            payload=message,
            ttl=message.ttl,
        )

        for node_id in route[1:]:
            packet.decrement_ttl()

            if packet.is_expired():
                return False

            node = self.registry.get(node_id)

            if node is None:
                return False

            if not node.is_online():
                return False

            self.forwarded_packets += 1

        self.delivered_packets += 1

        return True

    def send_packet(self, packet: Packet, route: List[str]) -> bool:
        """
        Generic packet forwarding.
        """

        if not route:
            return False

        if route[0] != packet.source:
            return False

        if route[-1] != packet.destination:
            return False

        for node_id in route[1:]:
            packet.decrement_ttl()

            if packet.is_expired():
                return False

            node = self.registry.get(node_id)

            if node is None:
                return False

            if not node.is_online():
                return False

            self.forwarded_packets += 1

        self.delivered_packets += 1

        return True

    def get_metrics(self):
        return {
            "forwarded_packets": self.forwarded_packets,
            "delivered_packets": self.delivered_packets,
        }