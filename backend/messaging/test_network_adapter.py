from backend.messaging.message import Message
from backend.messaging.network_adapter import NetworkAdapter


class FakeRouter:
    def find_route(self, source, destination):
        return [source, "B", destination]


class FakeNetwork:
    def __init__(self):
        self.router = FakeRouter()
        self.sent_messages = []

    def send_message(self, message, route):
        self.sent_messages.append(
            {
                "message": message,
                "route": route,
            }
        )
        return True


def test_adapter_finds_route():
    network = FakeNetwork()
    adapter = NetworkAdapter(network)

    route = adapter.find_route("A", "E")

    assert route == ["A", "B", "E"]


def test_adapter_sends_message():
    network = FakeNetwork()
    adapter = NetworkAdapter(network)

    message = Message.create(
        source="A",
        destination="E",
        payload="Emergency alert",
    )

    route = ["A", "B", "E"]

    result = adapter.send(message, route)

    assert result is True
    assert len(network.sent_messages) == 1
    assert network.sent_messages[0]["message"] == message
    assert network.sent_messages[0]["route"] == route