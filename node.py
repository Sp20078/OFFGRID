"""
OFFGRID real-node launcher.

Runs one physical OFFGRID node on this laptop:

    python node.py --id NODE_A --port 9001 --api-port 8001

- UDP transport (real sockets, LAN)
- UDP broadcast peer discovery
- multi-hop forwarding, store-and-forward, ACKs
- optional FastAPI API for the dashboard

Headless by default: the API server only starts when --api-port
(or --api / OFFGRID_API_PORT) is provided.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import List, Tuple

from backend.node_runtime.discovery import DiscoveryService
from backend.node_runtime.real_node import RealNode


def parse_peers(raw: str | None) -> List[Tuple[str, int]]:
    """
    Parse "--peers 192.168.1.102:9002,192.168.1.103:9003".
    """
    peers: List[Tuple[str, int]] = []

    if not raw:
        return peers

    for chunk in raw.split(","):
        chunk = chunk.strip()

        if not chunk:
            continue

        if ":" not in chunk:
            raise SystemExit(f"Invalid peer (expected ip:port): {chunk}")

        ip, _, port = chunk.rpartition(":")

        try:
            peers.append((ip.strip(), int(port)))
        except ValueError:
            raise SystemExit(f"Invalid peer port: {chunk}")

    return peers


def parse_links(raw: str | None) -> List[Tuple[str, str]]:
    """
    Parse "--links NODE_A:NODE_B,NODE_B:NODE_C" into edge pairs.

    Edges are treated as bidirectional by NetworkTopology.connect.
    """
    edges: List[Tuple[str, str]] = []

    if not raw:
        return edges

    for chunk in raw.split(","):
        chunk = chunk.strip()

        if not chunk:
            continue

        if ":" not in chunk:
            raise SystemExit(
                f"Invalid link (expected NODE_X:NODE_Y): {chunk}"
            )

        a, _, b = chunk.partition(":")
        edges.append((a.strip(), b.strip()))

    return edges


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="node.py",
        description="Start one real OFFGRID mesh node.",
    )

    parser.add_argument(
        "--id",
        dest="node_id",
        default=os.environ.get("NODE_ID", "NODE_A"),
        help="Logical node id, e.g. NODE_A (default: NODE_A)",
    )

    parser.add_argument(
        "--mode",
        choices=["real", "simulation"],
        default=os.environ.get("OFFGRID_MODE", "real"),
        help="real = actual UDP sockets; simulation = demo only",
    )

    parser.add_argument(
        "--host",
        default=os.environ.get("UDP_HOST", "0.0.0.0"),
        help="UDP bind address (default: 0.0.0.0)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("UDP_PORT", "9001")),
        help="UDP transport port (default: 9001)",
    )

    parser.add_argument(
        "--discovery",
        dest="discovery_port",
        type=int,
        default=int(os.environ.get("DISCOVERY_PORT", "9999")),
        help="UDP discovery/broadcast port (default: 9999)",
    )

    parser.add_argument(
        "--api-port",
        dest="api_port",
        type=int,
        default=None,
        help="FastAPI dashboard port, e.g. 8001 (optional)",
    )

    parser.add_argument(
        "--api",
        action="store_true",
        help="Enable the API on the default port for this node",
    )

    parser.add_argument(
        "--peers",
        default=os.environ.get("OFFGRID_PEERS", ""),
        help="Static peers, comma separated ip:port (fallback discovery)",
    )

    parser.add_argument(
        "--links",
        default=os.environ.get("OFFGRID_LINKS", ""),
        help=(
            "Restrict topology edges for demo chains, e.g. "
            "NODE_A:NODE_B,NODE_B:NODE_C (optional)"
        ),
    )

    parser.add_argument(
        "--heartbeat-interval",
        type=float,
        default=float(os.environ.get("HEARTBEAT_INTERVAL", "2")),
        help="Discovery/heartbeat announce interval seconds (default: 2)",
    )

    parser.add_argument(
        "--heartbeat-timeout",
        type=float,
        default=float(os.environ.get("HEARTBEAT_TIMEOUT", "6")),
        help="Peer considered offline after this many seconds (default: 6)",
    )

    parser.add_argument(
        "--check-network",
        action="store_true",
        help="Run connectivity diagnostics and exit",
    )

    return parser


def default_api_port(node_id: str) -> int:
    """
    NODE_A -> 8001, NODE_B -> 8002, ... based on the letter suffix.
    Falls back to 8000 when the id has no A-E suffix.
    """
    suffix = node_id.replace("NODE_", "").strip().upper()

    if len(suffix) == 1 and "A" <= suffix <= "E":
        return 8000 + (ord(suffix) - ord("A")) + 1

    return 8000


def run_check_network(args: argparse.Namespace) -> int:
    """Standalone diagnostics that do not bind the main ports."""
    print("=== OFFGRID NETWORK CHECK ===")
    print(f"Node ID        : {args.node_id}")
    print(f"LAN IP         : {DiscoveryService.local_ip()}")
    print(f"UDP bind       : {args.host}:{args.port}")
    print(f"Discovery port : {args.discovery_port}")

    # Broadcast capability probe.
    import socket

    ok = True

    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            print("Broadcast      : supported")
        finally:
            probe.close()
    except OSError as exc:
        ok = False
        print(f"Broadcast      : FAILED ({exc})")

    # Bind probe on the chosen UDP port.
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.bind((args.host, args.port))
            print(f"UDP bind test  : OK on {args.host}:{args.port}")
        finally:
            probe.close()
    except OSError as exc:
        ok = False
        print(f"UDP bind test  : FAILED ({exc})")

    print("=============================")
    print(
        "TIP: allow Python through your firewall for both private and"
        " public networks so discovery and packets can flow."
    )

    return 0 if ok else 1


async def amain(args: argparse.Namespace) -> None:
    node = RealNode(
        node_id=args.node_id,
        host=args.host,
        udp_port=args.port,
        discovery_port=args.discovery_port,
        api_host="0.0.0.0",
        api_port=args.api_port,
        static_peers=parse_peers(args.peers),
        links=parse_links(args.links),
        heartbeat_interval=args.heartbeat_interval,
        heartbeat_timeout=args.heartbeat_timeout,
    )

    await node.start()

    print()
    print("==============================================")
    print(f"  OFFGRID node {args.node_id} is running (REAL LAN MODE)")
    print(f"  Node ID        : {args.node_id}")
    print(f"  IP             : {DiscoveryService.local_ip()}")
    print(f"  UDP port       : {args.port}")
    print(f"  Discovery port : {args.discovery_port}")
    print(
        f"  API port       : {args.api_port if args.api_port else 'disabled'}"
    )
    print("  Press Ctrl+C to stop.")
    print("==============================================")
    print()

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await node.stop()


def main() -> int:
    args = build_parser().parse_args()

    if args.mode == "simulation":
        print(
            "Simulation mode is the legacy demo backend (backend/api/app.py):\n"
            "  uvicorn backend.api.app:app --port 8000\n"
            "For real multi-laptop networking, use: python node.py --mode real"
        )
        return 0

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    # Quiet uvicorn access logs; keep offgrid.* events visible.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    if args.api and args.api_port is None:
        args.api_port = default_api_port(args.node_id)

    if args.check_network:
        return run_check_network(args)

    try:
        asyncio.run(amain(args))
    except KeyboardInterrupt:
        print("\nNode stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
