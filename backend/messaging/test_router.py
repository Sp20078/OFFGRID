from .message import Message


class MockRouter:
    def __init__(self):
        self.online_nodes = set()

    def add_node(self, node: str):
        self.online_nodes.add(node)

    def remove_node(self, node: str):
        self.online_nodes.discard(node)

    def find_route(self, source: str, destination: str):
        if destination not in self.online_nodes:
            return None

        return [source, destination]

    def send(self, message: Message, route):
        if not route:
            return False

        return route[-1] in self.online_nodes