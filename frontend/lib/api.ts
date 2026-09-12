const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ??
  'http://127.0.0.1:8000';

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(
    `${API_BASE}${path}`,
    {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers ?? {}),
      },
      cache: 'no-store',
    },
  );

  if (!response.ok) {
    let message = `HTTP ${response.status}`;

    try {
      const body = await response.json();

      if (body?.detail) {
        message = body.detail;
      } else if (body?.message) {
        message = body.message;
      }
    } catch {
      // Ignore non-JSON error responses.
    }

    throw new Error(message);
  }

  return response.json();
}

// -----------------------------------------------------------------------------
// Nodes
// -----------------------------------------------------------------------------

export function getNodes() {
  return request<any[]>('/nodes');
}

export function getNode(nodeId: string) {
  return request<any>(
    `/nodes/${encodeURIComponent(nodeId)}`,
  );
}

// -----------------------------------------------------------------------------
// Topology
// -----------------------------------------------------------------------------

export function getTopology() {
  return request<any>('/network/topology');
}

export function getRoute(destination: string) {
  return request<any>(
    `/routes/${encodeURIComponent(destination)}`,
  );
}

// -----------------------------------------------------------------------------
// Metrics / events
// -----------------------------------------------------------------------------

export function getMetrics() {
  return request<any>('/metrics');
}

export function getEvents() {
  return request<any[]>('/events');
}

// -----------------------------------------------------------------------------
// Node simulation
// -----------------------------------------------------------------------------

export function killNode(nodeId: string) {
  return request<any>(
    `/node/${encodeURIComponent(nodeId)}/kill`,
    {
      method: 'POST',
    },
  );
}

export function restoreNode(nodeId: string) {
  return request<any>(
    `/node/${encodeURIComponent(nodeId)}/restore`,
    {
      method: 'POST',
    },
  );
}

// -----------------------------------------------------------------------------
// Internet simulation
// -----------------------------------------------------------------------------

export function toggleInternet(
  enabled: boolean,
) {
  const endpoint = enabled
    ? '/network/simulate/connect'
    : '/network/simulate/disconnect';

  return request<any>(endpoint, {
    method: 'POST',
  });
}

// -----------------------------------------------------------------------------
// Reset
// -----------------------------------------------------------------------------

export function resetNetwork() {
  return request<any>('/reset', {
    method: 'POST',
  });
}

// -----------------------------------------------------------------------------
// Messages
// -----------------------------------------------------------------------------

export function sendMessage(
  source: string,
  destination: string,
  payload: string,
) {
  return request<any>('/messages', {
    method: 'POST',
    body: JSON.stringify({
      source,
      destination,
      payload,
    }),
  });
}

// -----------------------------------------------------------------------------
// WebSocket
// -----------------------------------------------------------------------------

export function getWebSocketUrl() {
  if (
    typeof window !== 'undefined'
  ) {
    const protocol =
      window.location.protocol ===
      'https:'
        ? 'wss:'
        : 'ws:';

    return `${protocol}//${window.location.hostname}:8000/ws/network`;
  }

  const httpBase =
    process.env.NEXT_PUBLIC_API_URL ??
    'http://127.0.0.1:8000';

  return (
    httpBase.replace(/^http/, 'ws') +
    '/ws/network'
  );
}