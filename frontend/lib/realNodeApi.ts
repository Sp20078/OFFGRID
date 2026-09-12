/**
 * Client for the REAL LAN MODE node API (backend/api/real_api.py).
 *
 * One OFFGRID node exposes this API on its --api-port (e.g. 8001 for
 * NODE_A). The dashboard pointed at a node's API shows real discovered
 * peers and sends real UDP packets.
 */

export interface RealNodeSnapshotNode {
  id: string;
  label: string;
  status: 'ONLINE' | 'OFFLINE';
  ip: string;
  latencyMs: number;
  storedPacketsCount: number;
  x: number;
  y: number;
  neighbors: string[];
  lastSeenMs: number;
}

export interface RealNodeSnapshotLink {
  source: string;
  target: string;
  active: boolean;
  quality: number;
}

export interface RealNodeSnapshotLog {
  id: string;
  timestamp: string;
  level: string;
  message: string;
  nodeId?: string | null;
}

export interface RealNodeSnapshot {
  nodeId: string;
  mode: 'real';
  nodes: RealNodeSnapshotNode[];
  links: RealNodeSnapshotLink[];
  activeRoute: string[];
  metrics: {
    totalNodes: number;
    activeNodes: number;
    activeLinksCount: number;
    activePathHops: string[];
    internetAvailable: boolean;
    storeAndForwardQueueSize: number;
    avgMeshLatencyMs: number;
    forwardedPackets?: number;
    deliveredPackets?: number;
  };
  logs: RealNodeSnapshotLog[];
  inbox: Array<{
    message_id: string;
    source: string;
    destination: string;
    text: string;
    hop_count: number;
    received_at: number;
  }>;
  pendingMessages: Array<{ message_id: string; status: string }>;
}

export interface SendMessageResult {
  status: 'FORWARDED' | 'PENDING';
  message_id: string;
  source: string;
  destination: string;
  payload: string;
  route: string[];
}

const TIMEOUT_MS = 2500;

async function request<T>(baseUrl: string, path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const response = await fetch(`${baseUrl.replace(/\/$/, '')}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    });

    if (!response.ok) {
      const detail = await response.text().catch(() => response.statusText);
      throw new Error(`${response.status}: ${detail}`);
    }

    return (await response.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

export function fetchSnapshot(baseUrl: string): Promise<RealNodeSnapshot> {
  return request<RealNodeSnapshot>(baseUrl, '/network/topology');
}

export function fetchHealth(baseUrl: string): Promise<{ status: string; nodeId: string }> {
  return request<{ status: string; nodeId: string }>(baseUrl, '/health');
}

export interface LiveStateNode {
  id: string;
  status: 'ONLINE' | 'OFFLINE';
  ip: string;
}

export interface LiveStateMessage {
  message_id?: string;
  messageId?: string;
  source: string;
  destination: string;
  payload?: string;
  text?: string;
  status: string;
  created_at?: number;
  createdAt?: number;
}

export interface LiveStateEvent {
  id: string;
  timestamp: string;
  level: string;
  message: string;
  nodeId?: string | null;
}

export interface LiveState {
  nodeId: string;
  nodes: LiveStateNode[];
  messages: LiveStateMessage[];
  inbox: Array<{
    message_id: string;
    source: string;
    destination: string;
    text: string;
    hop_count: number;
    received_at: number;
  }>;
  events: LiveStateEvent[];
}

export function fetchLiveState(baseUrl: string): Promise<LiveState> {
  return request<LiveState>(baseUrl, '/state');
}

export function sendRealMessage(
  baseUrl: string,
  destination: string,
  payload: string,
  ttl: number = 10
): Promise<SendMessageResult> {
  return request<SendMessageResult>(baseUrl, '/messages', {
    method: 'POST',
    body: JSON.stringify({ destination, payload, ttl }),
  });
}
