from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.messaging.delivery import DeliveryManager
from backend.messaging.network_adapter import NetworkAdapter
from backend.network.heartbeat import HeartbeatManager
from backend.network.network import NetworkEngine
from backend.network.node import Node, NodeStatus
from backend.network.registry import NodeRegistry
from backend.network.router import Router
from backend.network.topology import NetworkTopology


# =============================================================================
# FastAPI
# =============================================================================

app = FastAPI(
    title="OFFGRID",
    description="Local-first decentralized mesh network",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request models
# =============================================================================

class MessageRequest(BaseModel):
    source: str = Field(
        default="NODE_A",
        min_length=1,
    )
    destination: str = Field(
        ...,
        min_length=1,
    )
    payload: str = Field(
        ...,
        min_length=1,
        max_length=5000,
    )
    ttl: int = Field(
        default=10,
        ge=1,
        le=64,
    )


class InternetRequest(BaseModel):
    enabled: bool


# =============================================================================
# Global network state
# =============================================================================

registry = NodeRegistry()
topology = NetworkTopology()
router = Router(
    topology=topology,
    registry=registry,
)

heartbeat = HeartbeatManager(
    registry=registry,
    timeout=15.0,
)

network_engine: NetworkEngine | None = None
delivery_manager: DeliveryManager | None = None

internet_available = True

events: list[dict[str, Any]] = []

websocket_clients: set[WebSocket] = set()

# Simple lock around mutable API state.
state_lock = asyncio.Lock()


# =============================================================================
# Utilities
# =============================================================================

def utc_now() -> str:
    return datetime.now(
        timezone.utc,
    ).isoformat()


def add_event(
    level: str,
    message: str,
    node_id: str | None = None,
) -> dict[str, Any]:
    """
    Add a uniquely identified event.

    UUIDs are used instead of len(events)+1 so the frontend
    never receives duplicate React keys.
    """
    event: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "timestamp": utc_now(),
        "level": level,
        "message": message,
    }

    if node_id is not None:
        event["nodeId"] = node_id

    events.append(event)

    # Keep memory bounded.
    if len(events) > 200:
        del events[:-200]

    return event


def node_to_frontend(node: Node) -> dict[str, Any]:
    """
    Convert backend Node to the structure expected by the
    Next.js dashboard.
    """
    # Fixed demo positions.
    positions: dict[str, tuple[float, float]] = {
        "NODE_A": (10.0, 50.0),
        "NODE_B": (30.0, 25.0),
        "NODE_C": (50.0, 50.0),
        "NODE_D": (70.0, 25.0),
        "NODE_E": (90.0, 50.0),
    }

    labels = {
        "NODE_A": "Node A",
        "NODE_B": "Node B",
        "NODE_C": "Node C",
        "NODE_D": "Node D",
        "NODE_E": "Node E",
    }

    x, y = positions.get(
        node.node_id,
        (50.0, 50.0),
    )

    node_status = (
        "ONLINE"
        if node.status == NodeStatus.ONLINE
        else "OFFLINE"
    )

    # Determine neighbor list from topology.
    neighbors = sorted(
        topology.neighbors(
            node.node_id,
        ),
    )

    latency = 20.0 if node_status == "ONLINE" else 0.0

    stored_packets = 0

    if delivery_manager is not None:
        try:
            stored_packets = len(
                delivery_manager.queue.get_for_destination(
                    node.node_id,
                )
            )
        except Exception:
            stored_packets = 0

    now_ms = int(
        datetime.now(
            timezone.utc,
        ).timestamp()
        * 1000
    )

    if node.last_seen is not None:
        try:
            last_seen_ms = int(
                node.last_seen.timestamp()
                * 1000
            )
        except Exception:
            last_seen_ms = now_ms
    else:
        last_seen_ms = now_ms

    return {
        "id": node.node_id,
        "label": labels.get(
            node.node_id,
            node.node_id,
        ),
        "status": node_status,
        "ip": node.address,
        "latencyMs": latency,
        "storedPacketsCount": stored_packets,
        "x": x,
        "y": y,
        "neighbors": neighbors,
        "lastSeenMs": last_seen_ms,
    }


def get_frontend_nodes() -> list[dict[str, Any]]:
    return [
        node_to_frontend(node)
        for node in registry.all_nodes()
    ]


def get_frontend_links() -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []

    graph = topology.get_graph()

    seen: set[tuple[str, str]] = set()

    for source, neighbors in graph.items():
        for target in neighbors:
            key = tuple(
                sorted(
                    (source, target),
                )
            )

            if key in seen:
                continue

            seen.add(key)

            source_node = registry.get(
                source,
            )
            target_node = registry.get(
                target,
            )

            if (
                source_node is None
                or target_node is None
            ):
                continue

            active = (
                source_node.is_online()
                and target_node.is_online()
            )

            links.append(
                {
                    "source": source,
                    "target": target,
                    "active": active,
                    "quality": 1.0
                    if active
                    else 0.0,
                }
            )

    return links


# =============================================================================
# Deterministic demo routing
# =============================================================================

def get_active_route(
    source: str = "NODE_A",
    destination: str = "NODE_E",
) -> list[str]:
    """
    Preserve the canonical demo route when healthy:

        A -> B -> C -> D -> E

    When C is offline:

        A -> B -> D -> E

    Otherwise fall back to the actual BFS router.
    """
    canonical = [
        "NODE_A",
        "NODE_B",
        "NODE_C",
        "NODE_D",
        "NODE_E",
    ]

    if source == "NODE_A" and destination == "NODE_E":
        all_online = all(
            (
                registry.get(node_id)
                is not None
                and registry.get(
                    node_id
                ).is_online()
            )
            for node_id in canonical
        )

        if all_online:
            return canonical

        node_c = registry.get("NODE_C")

        if (
            node_c is None
            or not node_c.is_online()
        ):
            backup = [
                "NODE_A",
                "NODE_B",
                "NODE_D",
                "NODE_E",
            ]

            if all(
                registry.get(node_id)
                is not None
                and registry.get(
                    node_id
                ).is_online()
                for node_id in backup
            ):
                return backup

    route = router.find_route(
        source,
        destination,
    )

    return route or []


def resolve_route(
    source: str,
    destination: str,
) -> list[str]:
    return get_active_route(
        source,
        destination,
    )


# =============================================================================
# Metrics
# =============================================================================

def get_metrics_payload() -> dict[str, Any]:
    nodes = registry.all_nodes()

    active_nodes = [
        node
        for node in nodes
        if node.is_online()
    ]

    links = get_frontend_links()

    active_links = [
        link
        for link in links
        if link["active"]
    ]

    route = get_active_route()

    queue_size = 0

    if delivery_manager is not None:
        try:
            queue_size = delivery_manager.queue.size()
        except Exception:
            queue_size = 0

    avg_latency = 20.0 if active_nodes else 0.0

    if network_engine is not None:
        metrics = network_engine.get_metrics()
    else:
        metrics = {
            "forwarded_packets": 0,
            "delivered_packets": 0,
        }

    return {
        "totalNodes": len(nodes),
        "activeNodes": len(active_nodes),
        "activeLinksCount": len(active_links),
        "activePathHops": route,
        "internetAvailable": internet_available,
        "storeAndForwardQueueSize": queue_size,
        "avgMeshLatencyMs": avg_latency,
        "forwardedPackets": metrics.get(
            "forwarded_packets",
            0,
        ),
        "deliveredPackets": metrics.get(
            "delivered_packets",
            0,
        ),
    }


def network_snapshot() -> dict[str, Any]:
    route = get_active_route()

    return {
        "nodes": get_frontend_nodes(),
        "links": get_frontend_links(),
        "activeRoute": route,
        "metrics": get_metrics_payload(),
        "logs": list(events[-100:]),
        "internetOnline": internet_available,
    }


# =============================================================================
# WebSocket broadcast
# =============================================================================

async def broadcast_network_state() -> None:
    if not websocket_clients:
        return

    payload = {
        "type": "NETWORK_STATE",
        "data": network_snapshot(),
    }

    dead_clients: list[WebSocket] = []

    for websocket in list(
        websocket_clients
    ):
        try:
            await websocket.send_json(
                payload
            )
        except Exception:
            dead_clients.append(
                websocket
            )

    for websocket in dead_clients:
        websocket_clients.discard(
            websocket
        )


async def emit_event(
    level: str,
    message: str,
    node_id: str | None = None,
) -> None:
    add_event(
        level,
        message,
        node_id,
    )

    await broadcast_network_state()


# =============================================================================
# Network initialization
# =============================================================================

def initialize_network() -> None:
    global network_engine
    global delivery_manager
    global internet_available

    registry = globals()["registry"]
    topology = globals()["topology"]
    router = globals()["router"]

    # Clean previous state.
    for node in registry.all_nodes():
        registry.remove(node.node_id)

    # Rebuild topology.
    # NetworkTopology has no universal clear() contract in the
    # existing code, so recreate it and update globals.
    new_topology = NetworkTopology()
    globals()["topology"] = new_topology

    topology = new_topology

    router = Router(
        topology=topology,
        registry=registry,
    )

    globals()["router"] = router

    # Demo addresses.
    demo_nodes = [
        Node(
            node_id="NODE_A",
            address="127.0.0.1",
            port=9001,
        ),
        Node(
            node_id="NODE_B",
            address="127.0.0.1",
            port=9002,
        ),
        Node(
            node_id="NODE_C",
            address="127.0.0.1",
            port=9003,
        ),
        Node(
            node_id="NODE_D",
            address="127.0.0.1",
            port=9004,
        ),
        Node(
            node_id="NODE_E",
            address="127.0.0.1",
            port=9005,
        ),
    ]

    for node in demo_nodes:
        registry.add(node)
        topology.add_node(
            node.node_id
        )
        registry.mark_online(
            node.node_id
        )

    # Main path.
    topology.connect(
        "NODE_A",
        "NODE_B",
    )
    topology.connect(
        "NODE_B",
        "NODE_C",
    )
    topology.connect(
        "NODE_C",
        "NODE_D",
    )
    topology.connect(
        "NODE_D",
        "NODE_E",
    )

    # Backup path.
    topology.connect(
        "NODE_B",
        "NODE_D",
    )

    network_engine = NetworkEngine(
        node=demo_nodes[0],
        registry=registry,
        topology=topology,
        router=router,
    )

    globals()[
        "network_engine"
    ] = network_engine

    adapter = NetworkAdapter(
        network_engine
    )

    delivery_manager = DeliveryManager(
        router=adapter,
        max_retries=3,
    )

    globals()[
        "delivery_manager"
    ] = delivery_manager

    internet_available = True

    events.clear()

    add_event(
        "SUCCESS",
        "OFFGRID network initialized.",
    )

    add_event(
        "INFO",
        "Healthy route established: NODE_A → NODE_B → NODE_C → NODE_D → NODE_E.",
    )

    add_event(
        "INFO",
        "Backup route available through NODE_B → NODE_D.",
    )


# =============================================================================
# Startup
# =============================================================================

@app.on_event("startup")
async def startup_event() -> None:
    initialize_network()


# =============================================================================
# Root / health
# =============================================================================

@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "name": "OFFGRID",
        "status": "running",
        "service": "decentralized mesh network",
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "nodes": registry.count(),
        "onlineNodes": registry.online_count(),
        "internetAvailable": internet_available,
    }


# =============================================================================
# Nodes
# =============================================================================

@app.get("/nodes")
async def get_nodes() -> list[dict[str, Any]]:
    return get_frontend_nodes()


@app.get("/nodes/{node_id}")
async def get_node(
    node_id: str,
) -> dict[str, Any]:
    node = registry.get(node_id)

    if node is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown node: {node_id}",
        )

    return node_to_frontend(node)


# =============================================================================
# Topology
# =============================================================================

@app.get("/network/topology")
async def get_topology() -> dict[str, Any]:
    return {
        "nodes": get_frontend_nodes(),
        "links": get_frontend_links(),
        "activeRoute": get_active_route(),
    }


# =============================================================================
# Routes
# =============================================================================

@app.get("/routes")
async def get_all_routes() -> dict[str, Any]:
    routes: dict[str, list[str]] = {}

    for node in registry.all_nodes():
        if node.node_id == "NODE_A":
            continue

        routes[node.node_id] = resolve_route(
            "NODE_A",
            node.node_id,
        )

    return routes


@app.get("/routes/{destination}")
async def get_route(
    destination: str,
) -> dict[str, Any]:
    if registry.get(destination) is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown destination: {destination}",
        )

    route = resolve_route(
        "NODE_A",
        destination,
    )

    return {
        "source": "NODE_A",
        "destination": destination,
        "route": route,
        "reachable": bool(route),
    }


# =============================================================================
# Metrics
# =============================================================================

@app.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    return get_metrics_payload()


# =============================================================================
# Events
# =============================================================================

@app.get("/events")
async def get_events() -> list[dict[str, Any]]:
    return list(events[-100:])


# =============================================================================
# Messaging
# =============================================================================

@app.get("/messages")
async def get_messages() -> dict[str, Any]:
    if delivery_manager is None:
        return {
            "messages": [],
            "count": 0,
        }

    messages = [
        message.to_dict()
        for message in delivery_manager.pending_messages()
    ]

    return {
        "messages": messages,
        "count": len(messages),
    }


@app.post("/messages")
async def post_message(
    request: MessageRequest,
) -> dict[str, Any]:
    if delivery_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Messaging system not initialized",
        )

    source_node = registry.get(
        request.source
    )

    destination_node = registry.get(
        request.destination
    )

    if source_node is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown source node: {request.source}",
        )

    if destination_node is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown destination node: "
                f"{request.destination}"
            ),
        )

    if not source_node.is_online():
        raise HTTPException(
            status_code=409,
            detail=f"Source node {request.source} is offline",
        )

    message = delivery_manager.create_message(
        source=request.source,
        destination=request.destination,
        payload=request.payload,
        ttl=request.ttl,
    )

    route = resolve_route(
        request.source,
        request.destination,
    )

    # -------------------------------------------------------------------------
    # No route: store-and-forward.
    # -------------------------------------------------------------------------

    if not route:
        delivery_manager.deliver(
            message
        )

        await emit_event(
            "WARN",
            (
                f"Message {message.message_id} "
                f"stored: no route to "
                f"{request.destination}."
            ),
            request.source,
        )

        return {
            "status": "PENDING",
            "message_id": message.message_id,
            "source": request.source,
            "destination": request.destination,
            "payload": request.payload,
            "route": [],
        }

    # -------------------------------------------------------------------------
    # Route exists.
    # -------------------------------------------------------------------------

    success = network_engine.send_message(
        message,
        route,
    )

    if success:
        delivery_manager.store.mark_forwarded(
            message.message_id
        )

        delivery_manager.acknowledge(
            message.message_id
        )

        await emit_event(
            "SUCCESS",
            (
                f"Message delivered "
                f"{request.source} → "
                f"{request.destination}: "
                f"\"{request.payload}\""
            ),
            request.source,
        )

        await emit_event(
            "INFO",
            (
                "Route used: "
                + " → ".join(route)
            ),
            request.source,
        )

        return {
            "status": "DELIVERED",
            "message_id": message.message_id,
            "source": request.source,
            "destination": request.destination,
            "payload": request.payload,
            "route": route,
        }

    # Fallback to queue if sending failed.
    delivery_manager.deliver(
        message
    )

    await emit_event(
        "WARN",
        (
            f"Message {message.message_id} "
            f"could not be delivered and "
            "was queued."
        ),
        request.source,
    )

    return {
        "status": "PENDING",
        "message_id": message.message_id,
        "source": request.source,
        "destination": request.destination,
        "payload": request.payload,
        "route": route,
    }


# =============================================================================
# Internet simulation
# =============================================================================

@app.post("/network/simulate/disconnect")
async def disconnect_internet() -> dict[str, Any]:
    global internet_available

    internet_available = False

    await emit_event(
        "WARN",
        "Internet connection simulated as OFFLINE. Mesh remains operational.",
    )

    return network_snapshot()


@app.post("/network/simulate/connect")
async def connect_internet() -> dict[str, Any]:
    global internet_available

    internet_available = True

    await emit_event(
        "SUCCESS",
        "Internet connection restored.",
    )

    return network_snapshot()


# =============================================================================
# Kill node
# =============================================================================

@app.post("/node/{node_id}/kill")
async def kill_node(
    node_id: str,
) -> dict[str, Any]:
    node = registry.get(node_id)

    if node is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown node: {node_id}",
        )

    if not node.is_online():
        return network_snapshot()

    registry.mark_offline(
        node_id
    )

    # Force routing to ignore this node.
    add_event(
        "WARN",
        f"{node_id} has been taken offline.",
        node_id,
    )

    new_route = get_active_route(
        "NODE_A",
        "NODE_E",
    )

    if new_route:
        add_event(
            "SUCCESS",
            (
                "Route recalculated: "
                + " → ".join(new_route)
            ),
        )
    else:
        add_event(
            "ERROR",
            "No route currently available to NODE_E.",
        )

    await broadcast_network_state()

    return network_snapshot()


# =============================================================================
# Restore node
# =============================================================================

@app.post("/node/{node_id}/restore")
async def restore_node(
    node_id: str,
) -> dict[str, Any]:
    node = registry.get(node_id)

    if node is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown node: {node_id}",
        )

    registry.mark_online(
        node_id
    )

    node.mark_seen()

    add_event(
        "SUCCESS",
        f"{node_id} has been restored to the mesh.",
        node_id,
    )

    # -------------------------------------------------------------------------
    # Try store-and-forward queue.
    # -------------------------------------------------------------------------

    if delivery_manager is not None:
        try:
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
                        f"Queued message "
                        f"{message_id} delivered "
                        f"after {node_id} returned."
                    ),
                    node_id,
                )

        except Exception as exc:
            add_event(
                "WARN",
                (
                    f"Retry processing for "
                    f"{node_id} failed: {exc}"
                ),
                node_id,
            )

    route = get_active_route(
        "NODE_A",
        "NODE_E",
    )

    if route:
        add_event(
            "INFO",
            (
                "Current route: "
                + " → ".join(route)
            ),
        )

    await broadcast_network_state()

    return network_snapshot()


# =============================================================================
# Reset
# =============================================================================

@app.post("/reset")
async def reset_network() -> dict[str, Any]:
    initialize_network()

    add_event(
        "SUCCESS",
        "Network reset to healthy demo state.",
    )

    await broadcast_network_state()

    return network_snapshot()


# =============================================================================
# WebSocket
# =============================================================================

@app.websocket("/ws/network")
async def websocket_network(
    websocket: WebSocket,
) -> None:
    await websocket.accept()

    websocket_clients.add(
        websocket
    )

    try:
        # Send current state immediately.
        await websocket.send_json(
            {
                "type": "NETWORK_STATE",
                "data": network_snapshot(),
            }
        )

        while True:
            try:
                message = await websocket.receive_text()

                # Optional heartbeat from frontend/client.
                if message.upper() == "PING":
                    await websocket.send_json(
                        {
                            "type": "PONG",
                        }
                    )

            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass

    except Exception as exc:
        print(
            f"WebSocket error: {exc}"
        )

    finally:
        websocket_clients.discard(
            websocket
        )


# =============================================================================
# Development entry point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )