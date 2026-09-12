from dataclasses import dataclass, field
from time import time
from uuid import uuid4
from typing import Any


@dataclass
class Packet:
    source: str
    destination: str
    payload: Any

    packet_id: str = field(default_factory=lambda: str(uuid4()))
    ttl: int = 8
    hop_count: int = 0
    timestamp: float = field(default_factory=time)

    def decrement_ttl(self):
        if self.ttl > 0:
            self.ttl -= 1

        self.hop_count += 1

    def is_expired(self):
        return self.ttl <= 0

    def to_dict(self):
        return {
            "packet_id": self.packet_id,
            "source": self.source,
            "destination": self.destination,
            "payload": self.payload,
            "ttl": self.ttl,
            "hop_count": self.hop_count,
            "timestamp": self.timestamp,
        }