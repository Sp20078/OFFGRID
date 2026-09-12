from dataclasses import dataclass, field
from time import time
from uuid import uuid4
from typing import Any


# Packet types used on the wire.
PACKET_TYPE_DATA = "DATA"
PACKET_TYPE_ACK = "ACK"
PACKET_TYPE_HEARTBEAT = "HEARTBEAT"
PACKET_TYPE_DISCOVERY = "DISCOVERY"

KNOWN_PACKET_TYPES = {
    PACKET_TYPE_DATA,
    PACKET_TYPE_ACK,
    PACKET_TYPE_HEARTBEAT,
    PACKET_TYPE_DISCOVERY,
}


@dataclass
class Packet:
    source: str
    destination: str
    payload: Any

    packet_id: str = field(default_factory=lambda: str(uuid4()))
    ttl: int = 8
    hop_count: int = 0
    timestamp: float = field(default_factory=time)
    packet_type: str = PACKET_TYPE_DATA

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
            "packet_type": self.packet_type,
        }

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "Packet":
        """
        Rebuild a packet from a wire dictionary.

        Raises ValueError on malformed input. Unknown packet types
        and non-string node ids are rejected for safety.
        """
        if not isinstance(data, dict):
            raise ValueError("packet must be a JSON object")

        required = (
            "packet_id",
            "source",
            "destination",
            "payload",
            "ttl",
        )

        for key in required:
            if key not in data:
                raise ValueError(f"missing field: {key}")

        packet_type = data.get("packet_type", PACKET_TYPE_DATA)

        if packet_type not in KNOWN_PACKET_TYPES:
            raise ValueError(f"unknown packet_type: {packet_type}")

        source = data["source"]
        destination = data["destination"]

        if not isinstance(source, str) or not source:
            raise ValueError("invalid source")

        if not isinstance(destination, str) or not destination:
            raise ValueError("invalid destination")

        if not isinstance(data["packet_id"], str) or not data["packet_id"]:
            raise ValueError("invalid packet_id")

        ttl = data["ttl"]

        if not isinstance(ttl, int) or ttl < 0:
            raise ValueError("invalid ttl")

        return cls(
            source=source,
            destination=destination,
            payload=data["payload"],
            packet_id=data["packet_id"],
            ttl=ttl,
            hop_count=int(data.get("hop_count", 0)),
            timestamp=float(data.get("timestamp", time())),
            packet_type=packet_type,
        )

    @classmethod
    def from_json(cls, raw: str) -> "Packet":
        import json

        return cls.from_dict(json.loads(raw))