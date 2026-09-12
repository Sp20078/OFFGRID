class MockRouter:
    def __init__(self):
        self.online_nodes = set()

    def add_node(self, node):
        self.online_nodes.add(node)

    def remove_node(self, node):
        self.online_nodes.discard(node)

    def find_route(self, destination):
        if destination not in self.online_nodes:
            return None

        return ["SOURCE", destination]

    def send(self, message, route):
        return route[-1] in self.online_nodes