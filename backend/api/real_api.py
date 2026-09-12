"""
FastAPI application for REAL LAN MODE nodes.

This is a separate app from the existing demo simulation
(backend/api/app.py). It exposes the same dashboard-shaped
endpoints, but every read reflects real discovered peers and
every POST /messages sends a real UDP packet.

Kept deliberately thin: all behaviour lives in RealNode and the
existing OFFGRID classes it composes.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.network.packet import Packet


class MessageRequest(BaseModel):
    """Body of POST /messages (module-level so FastAPI can resolve
    its annotation under `from __future__ import annotations`)."""

    destination: str = Field(..., min_length=1, max_length=64)
    payload: str = Field(..., min_length=1, max_length=5000)
    ttl: int = Field(default=10, ge=1, le=64)
    source: Optional[str] = Field(default=None, max_length=64)


def create_app(node) -> FastAPI:
    """
    Build the API app for the given RealNode instance.

    One RealNode runs at most one API server, so a module-level
    closure over the node is safe here.
    """
    app = FastAPI(
        title="OFFGRID Node",
        description=f"Real LAN node {node.node_id}",
        version="2.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Health / info
    # ------------------------------------------------------------------

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "name": "OFFGRID",
            "mode": "real",
            "nodeId": node.node_id,
            "status": "running",
        }

    @app.get("/health")
    async def health() -> dict[str, Any]:
        import socket

        return {
            "status": "ok",
            "mode": "real",
            "nodeId": node.node_id,
            "udp": {
                "host": node.host,
                "port": node.udp_port,
            },
            "discoveryPort": node.discovery_port,
            "apiPort": node.api_port,
            "lanIp": node.discovery.local_ip(),
            "peersDiscovered": len(node.discovery.peers),
            "onlineNodes": node.registry.online_count(),
            "nodes": node.registry.count(),
        }

    # ------------------------------------------------------------------
    # Dashboard-shaped endpoints (same shapes as the demo app)
    # ------------------------------------------------------------------

    @app.get("/nodes")
    async def get_nodes() -> list[dict[str, Any]]:
        return node.snapshot()["nodes"]

    @app.get("/network/topology")
    async def get_topology() -> dict[str, Any]:
        snap = node.snapshot()

        return {
            "nodes": snap["nodes"],
            "links": snap["links"],
            "activeRoute": snap["activeRoute"],
        }

    @app.get("/metrics")
    async def get_metrics() -> dict[str, Any]:
        return node.snapshot()["metrics"]

    @app.get("/events")
    async def get_events() -> list[dict[str, Any]]:
        return list(node.events)[-100:]

    # ------------------------------------------------------------------
    # Peers / routes
    # ------------------------------------------------------------------

    @app.get("/peers")
    async def get_peers() -> dict[str, Any]:
        return {
            "nodeId": node.node_id,
            "peers": [
                {
                    "nodeId": peer_id,
                    "ip": ip,
                    "udpPort": port,
                }
                for peer_id, (ip, port) in node.discovery.peers.items()
            ],
        }

    @app.get("/routes/{destination}")
    async def get_route(destination: str) -> dict[str, Any]:
        if destination == node.node_id:
            route: list[str] = [node.node_id]
        else:
            route = node.relay.find_route(node.node_id, destination) or []

        return {
            "source": node.node_id,
            "destination": destination,
            "route": route,
            "reachable": bool(route),
        }

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    @app.post("/messages")
    async def post_message(request: MessageRequest) -> dict[str, Any]:
        destination = request.destination

        if destination == node.node_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot send a message to yourself",
            )

        known = (
            node.topology.has_node(destination)
            or destination in node.discovery.peers
        )

        if not known:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown destination node: {destination}",
            )

        if request.source and request.source != node.node_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"This node is {node.node_id}; "
                    f"source must be omitted or equal to it"
                ),
            )

        result = node.send_custom_message(
            destination=destination,
            payload=request.payload,
            ttl=request.ttl,
        )

        return result

    @app.get("/messages")
    async def get_messages() -> dict[str, Any]:
        pending = node.delivery_manager.pending_messages()

        return {
            "messages": [m.to_dict() for m in pending],
            "count": len(pending),
        }

    @app.get("/inbox")
    async def get_inbox() -> dict[str, Any]:
        return {
            "nodeId": node.node_id,
            "inbox": list(node.relay.inbox)[-50:],
            "count": len(node.relay.inbox),
        }

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @app.post("/reset")
    async def reset_network() -> dict[str, Any]:
        """
        Reset local message state without tearing down the node.
        Discovered peers are kept (they are real machines, not
        simulated state).
        """
        node.delivery_manager.queue.clear()
        node.delivery_manager.store.messages.clear()
        node.relay.inbox.clear()
        node.relay.duplicates.clear()
        node.relay.stats = {
            key: 0
            for key in node.relay.stats
        }

        return {"status": "reset", "nodeId": node.node_id}

    @app.get("/check-network")
    async def check_network() -> dict[str, Any]:
        """
        Connectivity diagnostic: reports local interfaces and whether
        the UDP socket is bound and broadcast-capable.
        """
        import socket

        lan_ip = node.discovery.local_ip()

        sock_ok = node.transport.running

        broadcast_ok = False
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                broadcast_ok = True
            finally:
                probe.close()
        except OSError:
            pass

        return {
            "nodeId": node.node_id,
            "lanIp": lan_ip,
            "udpBound": sock_ok,
            "udpPort": node.udp_port,
            "broadcastCapable": broadcast_ok,
            "discoveryPort": node.discovery_port,
            "peersDiscovered": sorted(node.discovery.peers.keys()),
        }

    return app
