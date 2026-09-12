from collections import defaultdict, deque
from typing import List
from .message import Message


class StoreForwardQueue:
    def __init__(self):
        self.queues = defaultdict(deque)

    def store(self, message: Message):
        self.queues[message.destination].append(message)

    def get_for_destination(self, destination: str) -> List[Message]:
        return list(self.queues.get(destination, []))

    def pop_for_destination(self, destination: str) -> Message | None:
        queue = self.queues.get(destination)

        if not queue:
            return None

        return queue.popleft()

    def remove(self, message_id: str, destination: str):
        queue = self.queues.get(destination)

        if not queue:
            return

        self.queues[destination] = deque(
            message
            for message in queue
            if message.message_id != message_id
        )

    def size(self, destination: str = None):
        if destination:
            return len(self.queues.get(destination, []))

        return sum(len(queue) for queue in self.queues.values())

    def clear(self):
        self.queues.clear()