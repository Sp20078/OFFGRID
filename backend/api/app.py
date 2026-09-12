from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.messaging.delivery import DeliveryManager
from backend.messaging.network_adapter import NetworkAdapter
from backend.network.network import NetworkEngine
from backend.network.node import Node, NodeStatus
from backend.network.registry import NodeRegistry
from backend.network.router import Router
from backend.network.topology import NetworkTopology


# =============================================================================
# FastAPI
# =============================================================================

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


# =============================================================================
# Global OFFGRID state
# =============================================================================

registry = NodeRegistry()
topology = NetworkTopology()
router = Router(
    topology=topology,
    registry=registry,
)

network_engine: NetworkEngine | None = None
delivery_manager: DeliveryManager | None = None

INTERNET_AVAILABLE = False

EVENTS: list[dict[str, Any]] = []

connected_clients: set[WebSocket] = set()


# =============================================================================
# Demo node configuration
# =============================================================================

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

CANONICAL_DEMO_ROUTE = [
    "NODE_A",
    "NODE_B",
    "NODE_C",
    "NODE_D",
    "NODE_E",
]

BACKUP_DEMO_ROUTE = [
    "NODE_A",
    "NODE_B",
    "NODE_D",
    "NODE_E",
]


# =============================================================================
# Request models
# =============================================================================

class MessageRequest(BaseModel):
    source: str = "NODE_A"
    destination: str = "NODE_E"
    payload: str


# =============================================================================
# Events
# =============================================================================

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

    # Keep the UI event stream bounded.
    del EVENTS[50:]

    return event


# =============================================================================
# Network initialization
# =============================================================================

def initialize_network() -> None:
    global network_engine
    global delivery_manager

    registry.nodes.clear()
    topology.connections.clear()

    # -------------------------------------------------------------------------
    # Create nodes
    # -------------------------------------------------------------------------

    node_ids = list(NODE_COORDINATES.keys())

    for index, node_id in enumerate(node_ids):
        registry.add(
            Node(
                node_id=node_id,
                address=NODE_IPS[node_id],
                port=5000 + index,
            )
        )

    # -------------------------------------------------------------------------
    # Normal path:
    #
    # A -> B -> C -> D -> E
    # -------------------------------------------------------------------------

    for source, target in [
        ("NODE_A", "NODE_B"),
        ("NODE_B", "NODE_C"),
        ("NODE_C", "NODE_D"),
        ("NODE_D", "NODE_E"),
    ]:
        topology.connect(source, target)

    # -------------------------------------------------------------------------
    # Backup path:
    #
    # B -> D
    #
    # This becomes active when C is offline.
    # -------------------------------------------------------------------------

    topology.connect(
        "NODE_B",
        "NODE_D",
    )

    # -------------------------------------------------------------------------
    # Build network engine
    # -------------------------------------------------------------------------

    node_a = registry.get("NODE_A")

    if node_a is None:
        raise RuntimeError("NODE_A was not created")

    network_engine = NetworkEngine(
        node=node_a,
        registry=registry,
        topology=topology,
        router=router,
    )

    # Adapter allows DeliveryManager to use the network layer
    # without knowing its internal implementation.
    adapter = NetworkAdapter(network_engine)

    delivery_manager = DeliveryManager(
        router=adapter,
        max_retries=3,
    )


# =============================================================================
# Route helpers
# =============================================================================

def _all_nodes_online(route: list[str]) -> bool:
    for node_id in route:
        node = registry.get(node_id)

        if node is None or not node.is_online():
            return False

    return True


def get_active_route() -> list[str]:
    """
    Deterministic demo route.

    Healthy network:
        A -> B -> C -> D -> E

    C offline:
        A -> B -> D -> E
    """

    if _all_nodes_online(CANONICAL_DEMO_ROUTE):
        return CANONICAL_DEMO_ROUTE.copy()

    if _all_nodes_online(BACKUP_DEMO_ROUTE):
        return BACKUP_DEMO_ROUTE.copy()

    # For any future topology, fall back to the real router.
    route = router.find_route(
        "NODE_A",
        "NODE_E",
    )

    return route or []


def resolve_route(
    source: str,
    destination: str,
) -> list[str] | None:
    """
    Resolve a route.

    The presentation demo has a deterministic A -> E path:
      A -> B -> C -> D -> E

    and a deterministic fallback:
      A -> B -> D -> E

    Other source/destination combinations use the real router.
    """

    if (
        source == "NODE_A"
        and destination == "NODE_E"
    ):
        route = get_active_route()

        return route or None

    return router.find_route(
        source,
        destination,
    )


# =============================================================================
# Snapshot helpers
# =============================================================================

def node_payload(node_id: str) -> dict[str, Any]:
    node = registry.get(node_id)

    if node is None:
        raise KeyError(node_id)

    x, y = NODE_COORDINATES[node_id]

    neighbors = topology.neighbors(node_id)

    status = (
        "OFFLINE"
        if node.status == NodeStatus.OFFLINE
        else "ONLINE"
    )

    return {
        "id": node_id,
        "label": NODE_LABELS[node_id],
        "status": status,
        "ip": node.address,
        "latencyMs": 0 if status == "OFFLINE" else 20,
        "storedPacketsCount": (
            0
            if delivery_manager is None
            else len(
                delivery_manager.pending_messages(node_id)
            )
        ),
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
                )
                * 1000
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


def get_queue_size() -> int:
    if delivery_manager is None:
        return 0

    return len(
        delivery_manager.pending_messages()
    )


def network_snapshot() -> dict[str, Any]:
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
            sum(active_latencies)
            / len(active_latencies)
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
            "storeAndForwardQueueSize": get_queue_size(),
            "avgMeshLatencyMs": avg_latency,
        },
        "logs": EVENTS,
    }


# =============================================================================
# WebSocket broadcasting
# =============================================================================

async def broadcast_state() -> None:
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


# =============================================================================
# Startup
# =============================================================================

initialize_network()

add_event(
    "INFO",
    "OFFGRID Core initializing P2P discovery...",
)

add_event(
    "SUCCESS",
    "Initial mesh topology ready.",
)

add_event(
    "SUCCESS",
    "Primary route: A → B → C → D → E",
)


# =============================================================================
# Basic endpoints
# =============================================================================

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


# =============================================================================
# Nodes
# =============================================================================

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


# =============================================================================
# Topology
# =============================================================================

@app.get("/network/topology")
def get_topology():
    snapshot = network_snapshot()

    return {
        "nodes": snapshot["nodes"],
        "links": snapshot["links"],
        "activeRoute": snapshot["activeRoute"],
    }


# =============================================================================
# Routes
# =============================================================================

@app.get("/routes")
def get_routes():
    return {
        "routes": {
            "NODE_E": get_active_route(),
        }
    }


@app.get("/routes/{destination}")
def get_route(destination: str):
    route = resolve_route(
        "NODE_A",
        destination,
    )

    return {
        "route": route or [],
    }


# =============================================================================
# Metrics / Events
# =============================================================================

@app.get("/metrics")
def get_metrics():
    return network_snapshot()["metrics"]


@app.get("/events")
def get_events():
    return EVENTS


# =============================================================================
# Messaging
# =============================================================================

@app.get("/messages")
def get_messages():
    if delivery_manager is None:
        return []

    return [
        message.to_dict()
        for message in delivery_manager.store.all()
    ]


@app.post("/messages")
async def send_message(request: MessageRequest):
    if delivery_manager is None:
        raise HTTPException(
            status_code=500,
            detail="Messaging system is not initialized",
        )

    # -------------------------------------------------------------------------
    # Create a real OFFGRID message
    # -------------------------------------------------------------------------

    message = delivery_manager.create_message(
        source=request.source,
        destination=request.destination,
        payload=request.payload,
        ttl=8,
        sequence=0,
    )

    # -------------------------------------------------------------------------
    # Resolve route
    # -------------------------------------------------------------------------

    route = resolve_route(
        request.source,
        request.destination,
    )

    # -------------------------------------------------------------------------
    # No route -> store and forward
    # -------------------------------------------------------------------------

    if route is None:
        delivery_manager.deliver(message)

        add_event(
            "WARN",
            (
                f"Destination {request.destination} unavailable. "
                f"Message stored locally."
            ),
        )

        await broadcast_state()

        return {
            "status": "PENDING",
            "messageId": message.message_id,
            "route": [],
        }

    # -------------------------------------------------------------------------
    # Use the exact route selected by the demo/router.
    #
    # This is important because DeliveryManager normally asks its router
    # for a route again. Here we deliberately execute the route selected
    # above so the dashboard and actual forwarding agree.
    # -------------------------------------------------------------------------

    if network_engine is None:
        raise HTTPException(
            status_code=500,
            detail="Network engine is not initialized",
        )

    delivered = network_engine.send_message(
        message,
        route,
    )

    if not delivered:
        delivery_manager.queue.store(message)

        add_event(
            "WARN",
            (
                f"Message {message.message_id} could not be delivered. "
                f"Stored for retry."
            ),
        )

        await broadcast_state()

        return {
            "status": "PENDING",
            "messageId": message.message_id,
            "route": route,
        }

    # -------------------------------------------------------------------------
    # Mark forwarded and then acknowledge.
    # -------------------------------------------------------------------------

    delivery_manager.store.mark_forwarded(
        message.message_id
    )

    delivery_manager.acknowledge(
        message.message_id
    )

    add_event(
        "INFO",
        (
            f"Packet forwarding route: "
            f"{' → '.join(route)}"
        ),
    )

    add_event(
        "SUCCESS",
        (
            f"Message {message.message_id} delivered "
            f"to {request.destination}."
        ),
    )

    await broadcast_state()

    return {
        "status": "DELIVERED",
        "messageId": message.message_id,
        "route": route,
    }


# =============================================================================
# Internet simulation
# =============================================================================

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


# =============================================================================
# Node failure simulation
# =============================================================================

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
        (
            f"{NODE_LABELS[node_id]} restored. "
            f"Heartbeat re-established."
        ),
        node_id,
    )

    # -------------------------------------------------------------------------
    # If this node is a pending-message destination, retry stored packets.
    # -------------------------------------------------------------------------

    if delivery_manager is not None:
        pending_before = (
            delivery_manager.pending_messages(node_id)
        )

        if pending_before:
            delivered_ids = (
                delivery_manager.retry_pending(
                    node_id
                )
            )

            for message_id in delivered_ids:
                delivery_manager.acknowledge(
                    message_id
                )

                add_event(
                    "SUCCESS",
                    (
                        f"Stored message {message_id} "
                        f"forwarded to {node_id}."
                    ),
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


# =============================================================================
# Reset
# =============================================================================

@app.post("/network/reset")
async def reset_network():
    global INTERNET_AVAILABLE

    INTERNET_AVAILABLE = False

    EVENTS.clear()

    initialize_network()

    # Reinitialize pending messaging state as well.
    add_event(
        "INFO",
        "Network topology reset to initial state.",
    )

    add_event(
        "SUCCESS",
        "Primary route restored: A → B → C → D → E",
    )

    await broadcast_state()

    return network_snapshot()


# =============================================================================
# WebSocket
# =============================================================================

@app.websocket("/ws/network")
async def network_websocket(websocket: WebSocket):
    await websocket.accept()

    connected_clients.add(websocket)

    try:
        # Immediately send current state.
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