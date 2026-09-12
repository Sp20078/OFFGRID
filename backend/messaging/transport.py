from typing import List, Protocol

from .message import Message


class MessageTransport(Protocol):
    """
    Interface between the messaging layer and the network layer.

    Person 3's messaging code depends on this interface.
    Person 1's network implementation can satisfy it.
    """

    def find_route(
        self,
        source: str,
        destination: str,
    ) -> List[str] | None:
        ...

    def send(
        self,
        message: Message,
        route: List[str],
    ) -> bool:
        ...