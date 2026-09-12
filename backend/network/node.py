from dataclasses import dataclass, field
from enum import Enum
from time import time


class NodeStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


@dataclass
class Node:
    node_id: str
    address: str
    port: int
    status: NodeStatus = NodeStatus.ONLINE
    last_seen: float = field(default_factory=time)

    def mark_seen(self):
        self.last_seen = time()
        self.status = NodeStatus.ONLINE

    def mark_offline(self):
        self.status = NodeStatus.OFFLINE

    def is_online(self):
        return self.status == NodeStatus.ONLINE

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "address": self.address,
            "port": self.port,
            "status": self.status.value,
            "last_seen": self.last_seen,
        }