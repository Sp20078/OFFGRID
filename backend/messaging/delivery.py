from .message import Message, MessageStatus
from .store import MessageStore
from .duplicate import DuplicateDetector
from .queue import StoreForwardQueue
from .transport import MessageTransport


class DeliveryManager:
    def __init__(
        self,
        router: MessageTransport | None = None,
        max_retries: int = 3,
    ):
        self.router = router
        self.store = MessageStore()
        self.queue = StoreForwardQueue()
        self.duplicates = DuplicateDetector()
        self.max_retries = max_retries
        self.retry_counts: dict[str, int] = {}

    def create_message(
        self,
        source: str,
        destination: str,
        payload: str,
        ttl: int = 8,
        sequence: int = 0,
    ) -> Message:
        message = Message.create(
            source=source,
            destination=destination,
            payload=payload,
            ttl=ttl,
            sequence=sequence,
        )

        self.store.add(message)
        self.retry_counts[message.message_id] = 0

        return message

    def receive(self, message: Message) -> str:
        """
        Accept an incoming message unless it is a duplicate or expired.
        """
        if self.duplicates.check_and_mark(message.message_id):
            return "DUPLICATE"

        if message.is_expired():
            message.status = MessageStatus.EXPIRED
            self.store.add(message)
            return "EXPIRED"

        self.store.add(message)

        return "ACCEPTED"

    def deliver(self, message: Message) -> bool:
        """
        Attempt to send a message through the network router.

        If no route exists, the message is placed into the
        store-and-forward queue.
        """
        if message.is_expired():
            self.store.mark_expired(message.message_id)

            self.queue.remove(
                message.message_id,
                message.destination,
            )

            return False

        if self.router is None:
            self.queue.store(message)
            return False

        route = self.router.find_route(
            message.source,
            message.destination,
        )

        if not route:
            self.queue.store(message)
            return False

        send_method = getattr(self.router, "send", None)

        if send_method is None:
            self.queue.store(message)
            return False

        success = send_method(message, route)

        if success:
            self.store.mark_forwarded(message.message_id)
        else:
            self.queue.store(message)

        return success

    def acknowledge(self, message_id: str) -> bool:
        """
        Mark a message as delivered after receiving its ACK.
        """
        message = self.store.get(message_id)

        if message is None:
            return False

        if message.status == MessageStatus.EXPIRED:
            return False

        self.store.mark_delivered(message_id)

        self.queue.remove(
            message.message_id,
            message.destination,
        )

        self.retry_counts.pop(message_id, None)

        return True

    def retry_message(self, message: Message) -> bool:
        """
        Retry delivery up to max_retries.
        """
        message_id = message.message_id

        if message.is_expired():
            self.store.mark_expired(message_id)

            self.queue.remove(
                message_id,
                message.destination,
            )

            return False

        retries = self.retry_counts.get(message_id, 0)

        if retries >= self.max_retries:
            return False

        self.retry_counts[message_id] = retries + 1

        return self.deliver(message)

    def retry_pending(self, destination: str):
        """
        Retry all queued messages waiting for a destination.
        """
        messages = self.queue.get_for_destination(destination)

        delivered = []

        for message in messages:
            if message.is_expired():
                self.store.mark_expired(message.message_id)

                self.queue.remove(
                    message.message_id,
                    message.destination,
                )

                continue

            success = self.retry_message(message)

            if success:
                delivered.append(message.message_id)

                self.queue.remove(
                    message.message_id,
                    message.destination,
                )

        return delivered

    def decrement_ttl(self, message_id: str) -> bool:
        """
        Decrease the TTL of a stored message.

        Returns False when the message expires.
        """
        message = self.store.get(message_id)

        if message is None:
            return False

        message.decrement_ttl()

        if message.is_expired():
            self.store.mark_expired(message_id)

            self.queue.remove(
                message.message_id,
                message.destination,
            )

            return False

        return True

    def get_retry_count(self, message_id: str) -> int:
        return self.retry_counts.get(message_id, 0)

    def pending_messages(self, destination: str | None = None):
        """
        Return queued store-and-forward messages.
        """
        if destination:
            return self.queue.get_for_destination(destination)

        return [
            message
            for destination_id in self.queue.queues
            for message in self.queue.get_for_destination(destination_id)
        ]