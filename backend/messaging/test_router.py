class MockRouter:
    def __init__(self):
        self.online_nodes = set()

    def add_node(self, node):
        self.online_nodes.add(node)

    def remove_node(self, node):
        self.online_nodes.discard(node)

    def find_route(self, source, destination):
        """
        Test router.

        For messaging unit tests, we only simulate whether the
        destination is reachable. The real network router will
        handle source availability and multi-hop routing.
        """
        if destination not in self.online_nodes:
            return None

        return [source, destination]

    def send(self, message, route):
        if not route:
            return False

        return route[-1] in self.online_nodes