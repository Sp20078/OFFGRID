from typing import Dict, List, Optional
from .message import Message, MessageStatus


class MessageStore:
    def __init__(self):
        self.messages: Dict[str, Message] = {}

    def add(self, message: Message):
        self.messages[message.message_id] = message

    def get(self, message_id: str) -> Optional[Message]:
        return self.messages.get(message_id)

    def remove(self, message_id: str):
        self.messages.pop(message_id, None)

    def mark_delivered(self, message_id: str):
        message = self.get(message_id)
        if message:
            message.status = MessageStatus.DELIVERED

    def mark_forwarded(self, message_id: str):
        message = self.get(message_id)
        if message:
            message.status = MessageStatus.FORWARDED

    def mark_expired(self, message_id: str):
        message = self.get(message_id)
        if message:
            message.status = MessageStatus.EXPIRED

    def pending(self) -> List[Message]:
        return [
            message
            for message in self.messages.values()
            if message.status == MessageStatus.PENDING
        ]

    def for_destination(self, destination: str) -> List[Message]:
        return [
            message
            for message in self.pending()
            if message.destination == destination
        ]

    def all(self) -> List[Message]:
        return list(self.messages.values())

    def count(self):
        return len(self.messages)

    def pending_count(self):
        return len(self.pending())