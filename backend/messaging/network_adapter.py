from typing import List

from .message import Message
from .transport import MessageTransport


class NetworkAdapter(MessageTransport):
    """
    Connects the messaging layer to the OFFGRID network layer.

    The network object must provide:

        network.router.find_route(source, destination)
        network.send_message(message, route)
    """

    def __init__(self, network):
        self.network = network

    def find_route(
        self,
        source: str,
        destination: str,
    ) -> List[str] | None:
        return self.network.router.find_route(
            source,
            destination,
        )

    def send(
        self,
        message: Message,
        route: List[str],
    ) -> bool:
        return self.network.send_message(
            message,
            route,
        )