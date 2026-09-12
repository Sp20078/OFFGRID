from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.network.node import Node, NodeStatus
from backend.network.registry import NodeRegistry
from backend.network.router import Router
from backend.network.topology import NetworkTopology


app = FastAPI(
    title="OFFGRID API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Demo network state
# ---------------------------------------------------------------------------

registry = NodeRegistry()
topology = NetworkTopology()
router = Router(
    topology=topology,
    registry=registry,
)

INTERNET_AVAILABLE = False

EVENTS: list[dict[str, Any]] = []

NODE_COORDINATES = {
    "NODE_A": (14, 50),
    "NODE_B": (32, 25),
    "NODE_C": (50, 25),
    "NODE_D": (68, 65),
    "NODE_E": (86, 50),
}

NODE_LABELS = {
    "NODE_A": "Node A (Origin)",
    "NODE_B": "Node B (Relay 1)",
    "NODE_C": "Node C (Relay 2)",
    "NODE_D": "Node D (Relay 3)",
    "NODE_E": "Node E (Target)",
}

NODE_IPS = {
    "NODE_A": "10.0.0.1",
    "NODE_B": "10.0.0.2",
    "NODE_C": "10.0.0.3",
    "NODE_D": "10.0.0.4",
    "NODE_E": "10.0.0.5",
}


class MessageRequest(BaseModel):
    source: str = "NODE_A"
    destination: str = "NODE_E"
    payload: str


# ---------------------------------------------------------------------------
# WebSocket clients
# ---------------------------------------------------------------------------

connected_clients: set[WebSocket] = set()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def initialize_network() -> None:
    """Reset the in-memory demo network to its initial state."""

    registry.nodes.clear()
    topology.connections.clear()

    for index, node_id in enumerate(NODE_COORDINATES):
        registry.add(
            Node(
                node_id=node_id,
                address=NODE_IPS[node_id],
                port=5000 + index,
            )
        )

    # Main route:
    # A -> B -> C -> D -> E

    for source, target in [
        ("NODE_A", "NODE_B"),
        ("NODE_B", "NODE_C"),
        ("NODE_C", "NODE_D"),
        ("NODE_D", "NODE_E"),
    ]:
        topology.connect(source, target)

    # Backup route:
    # B -> D
    topology.connect("NODE_B", "NODE_D")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def add_event(
    level: str,
    message: str,
    node_id: str | None = None,
) -> dict[str, Any]:
    event = {
        "id": str(len(EVENTS) + 1),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "message": message,
    }

    if node_id is not None:
        event["nodeId"] = node_id

    EVENTS.insert(0, event)

    del EVENTS[50:]

    return event


def get_active_route() -> list[str]:
    """
    Demo route selection.

    Healthy network:
        A -> B -> C -> D -> E

    If C is offline:
        A -> B -> D -> E
    """

    node_c = registry.get("NODE_C")

    if node_c and node_c.is_online():
        route = router.find_route(
            "NODE_A",
            "NODE_E",
        )

        # Prefer the canonical demo route while C is alive.
        canonical = [
            "NODE_A",
            "NODE_B",
            "NODE_C",
            "NODE_D",
            "NODE_E",
        ]

        if route and all(
            registry.get(node_id) is not None
            and registry.get(node_id).is_online()
            for node_id in canonical
        ):
            return canonical

        return route or []

    # C is unavailable, so use the backup route.
    backup = [
        "NODE_A",
        "NODE_B",
        "NODE_D",
        "NODE_E",
    ]

    if all(
        registry.get(node_id) is not None
        and registry.get(node_id).is_online()
        for node_id in backup
    ):
        return backup

    return []


def node_payload(node_id: str) -> dict[str, Any]:
    node = registry.get(node_id)

    if node is None:
        raise KeyError(node_id)

    x, y = NODE_COORDINATES[node_id]

    neighbors = topology.neighbors(node_id)

    if node.status == NodeStatus.OFFLINE:
        status = "OFFLINE"
    else:
        status = "ONLINE"

    return {
        "id": node_id,
        "label": NODE_LABELS[node_id],
        "status": status,
        "ip": node.address,
        "latencyMs": 0 if status == "OFFLINE" else 20,
        "storedPacketsCount": 0,
        "x": x,
        "y": y,
        "neighbors": [
            NODE_LABELS.get(neighbor, neighbor)
            for neighbor in neighbors
        ],
        "lastSeenMs": max(
            0,
            int(
                (
                    datetime.now().timestamp()
                    - node.last_seen
                ) * 1000
            ),
        ),
    }


def links_payload() -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []

    seen: set[tuple[str, str]] = set()

    for source in topology.connections:
        for target in topology.connections[source]:

            pair = tuple(sorted((source, target)))

            if pair in seen:
                continue

            seen.add(pair)

            source_node = registry.get(source)
            target_node = registry.get(target)

            active = bool(
                source_node
                and target_node
                and source_node.is_online()
                and target_node.is_online()
            )

            links.append(
                {
                    "source": source,
                    "target": target,
                    "active": active,
                    "quality": 100 if active else 0,
                }
            )

    return links


def network_snapshot() -> dict[str, Any]:
    """Return the full state expected by the Next.js dashboard."""

    nodes = [
        node_payload(node_id)
        for node_id in NODE_COORDINATES
    ]

    links = links_payload()
    active_route = get_active_route()

    active_nodes = [
        node
        for node in nodes
        if node["status"] != "OFFLINE"
    ]

    active_links_count = sum(
        1
        for link in links
        if link["active"]
    )

    active_latencies = [
        node["latencyMs"]
        for node in active_nodes
        if node["latencyMs"] > 0
    ]

    avg_latency = (
        round(
            sum(active_latencies) / len(active_latencies)
        )
        if active_latencies
        else 0
    )

    return {
        "nodes": nodes,
        "links": links,
        "activeRoute": active_route,
        "internetOnline": INTERNET_AVAILABLE,
        "metrics": {
            "totalNodes": len(nodes),
            "activeNodes": len(active_nodes),
            "activeLinksCount": active_links_count,
            "activePathHops": active_route,
            "internetAvailable": INTERNET_AVAILABLE,
            "storeAndForwardQueueSize": 0,
            "avgMeshLatencyMs": avg_latency,
        },
        "logs": EVENTS,
    }


async def broadcast_state() -> None:
    """Push the latest state to every connected dashboard."""

    if not connected_clients:
        return

    payload = {
        "type": "NETWORK_STATE",
        "data": network_snapshot(),
    }

    disconnected: list[WebSocket] = []

    for client in connected_clients:
        try:
            await client.send_json(payload)
        except Exception:
            disconnected.append(client)

    for client in disconnected:
        connected_clients.discard(client)


initialize_network()

add_event(
    "INFO",
    "OFFGRID Core initializing P2P discovery...",
)

add_event(
    "SUCCESS",
    "Initial mesh topology ready.",
)


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "service": "OFFGRID",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "offgrid",
    }


@app.get("/nodes")
def get_nodes():
    return network_snapshot()["nodes"]


@app.get("/nodes/{node_id}")
def get_node(node_id: str):
    if not registry.contains(node_id):
        raise HTTPException(
            status_code=404,
            detail="Node not found",
        )

    return node_payload(node_id)


@app.get("/network/topology")
def get_topology():
    snapshot = network_snapshot()

    return {
        "nodes": snapshot["nodes"],
        "links": snapshot["links"],
        "activeRoute": snapshot["activeRoute"],
    }


@app.get("/routes")
def get_routes():
    route = get_active_route()

    return {
        "routes": {
            "NODE_E": route,
        },
    }


@app.get("/routes/{destination}")
def get_route(destination: str):
    route = router.find_route(
        "NODE_A",
        destination,
    )

    return {
        "route": route or [],
    }


@app.get("/metrics")
def get_metrics():
    return network_snapshot()["metrics"]


@app.get("/events")
def get_events():
    return EVENTS


@app.get("/messages")
def get_messages():
    return []


@app.post("/messages")
async def send_message(request: MessageRequest):
    route = router.find_route(
        request.source,
        request.destination,
    )

    if route is None:
        event = add_event(
            "WARN",
            (
                f"No route available from "
                f"{request.source} to {request.destination}. "
                "Message waiting for destination."
            ),
        )

        await broadcast_state()

        return {
            "status": "PENDING",
            "route": [],
            "event": event,
        }

    add_event(
        "INFO",
        f"Route resolved: {' → '.join(route)}",
    )

    add_event(
        "SUCCESS",
        f"Message delivered to {request.destination}.",
    )

    await broadcast_state()

    return {
        "status": "DELIVERED",
        "route": route,
    }


# ---------------------------------------------------------------------------
# Network simulation
# ---------------------------------------------------------------------------

@app.post("/network/simulate/disconnect")
async def disconnect_internet():
    global INTERNET_AVAILABLE

    INTERNET_AVAILABLE = False

    add_event(
        "WARN",
        "WAN connection severed. OFFGRID P2P fallback active.",
    )

    await broadcast_state()

    return network_snapshot()


@app.post("/network/simulate/connect")
async def connect_internet():
    global INTERNET_AVAILABLE

    INTERNET_AVAILABLE = True

    add_event(
        "SUCCESS",
        "WAN gateway restored.",
    )

    await broadcast_state()

    return network_snapshot()


@app.post("/network/simulate/node/{node_id}/kill")
async def kill_node(node_id: str):
    if not registry.contains(node_id):
        raise HTTPException(
            status_code=404,
            detail="Node not found",
        )

    registry.mark_offline(node_id)

    add_event(
        "ERROR",
        f"{NODE_LABELS[node_id]} offline. Connection lost.",
        node_id,
    )

    route = get_active_route()

    if route:
        add_event(
            "SUCCESS",
            f"Route recalculated: {' → '.join(route)}",
        )
    else:
        add_event(
            "ERROR",
            "No route currently available to NODE_E.",
        )

    await broadcast_state()

    return network_snapshot()


@app.post("/network/simulate/node/{node_id}/restore")
async def restore_node(node_id: str):
    if not registry.contains(node_id):
        raise HTTPException(
            status_code=404,
            detail="Node not found",
        )

    registry.mark_online(node_id)

    add_event(
        "SUCCESS",
        f"{NODE_LABELS[node_id]} restored. Heartbeat re-established.",
        node_id,
    )

    route = get_active_route()

    if route:
        add_event(
            "SUCCESS",
            f"Route restored: {' → '.join(route)}",
        )

    await broadcast_state()

    return network_snapshot()


@app.post("/network/reset")
async def reset_network():
    global INTERNET_AVAILABLE

    INTERNET_AVAILABLE = False

    initialize_network()
    EVENTS.clear()

    add_event(
        "INFO",
        "Network topology reset to initial state.",
    )

    add_event(
        "SUCCESS",
        "Initial route restored.",
    )

    await broadcast_state()

    return network_snapshot()


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws/network")
async def network_websocket(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)

    try:
        await websocket.send_json(
            {
                "type": "NETWORK_STATE",
                "data": network_snapshot(),
            }
        )

        while True:
            message = await websocket.receive_text()

            if message == "ping":
                await websocket.send_json(
                    {
                        "type": "PONG",
                    }
                )

    except WebSocketDisconnect:
        connected_clients.discard(websocket)

    except Exception:
        connected_clients.discard(websocket)