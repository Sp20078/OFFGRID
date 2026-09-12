from dataclasses import dataclass, asdict
from enum import Enum
from time import time
from uuid import uuid4
import json


class MessageStatus(str, Enum):
    PENDING = "PENDING"
    FORWARDED = "FORWARDED"
    DELIVERED = "DELIVERED"
    EXPIRED = "EXPIRED"


@dataclass
class Message:
    message_id: str
    source: str
    destination: str
    payload: str
    timestamp: float
    ttl: int
    sequence: int
    status: MessageStatus = MessageStatus.PENDING

    @classmethod
    def create(
        cls,
        source: str,
        destination: str,
        payload: str,
        ttl: int = 8,
        sequence: int = 0
    ):
        return cls(
            message_id=str(uuid4()),
            source=source,
            destination=destination,
            payload=payload,
            timestamp=time(),
            ttl=ttl,
            sequence=sequence
        )

    def decrement_ttl(self):
        if self.ttl > 0:
            self.ttl -= 1

    def is_expired(self):
        return self.ttl <= 0

    def to_dict(self):
        data = asdict(self)
        data["status"] = self.status.value
        return data

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data):
        data = data.copy()
        data["status"] = MessageStatus(data["status"])
        return cls(**data)

    @classmethod
    def from_json(cls, data):
        return cls.from_dict(json.loads(data))