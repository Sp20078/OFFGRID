const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';

export async function getNodes() {
  const response = await fetch(`${API_BASE}/nodes`, {
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch nodes: ${response.status}`);
  }

  return response.json();
}

export async function getTopology() {
  const response = await fetch(`${API_BASE}/network/topology`, {
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch topology: ${response.status}`);
  }

  return response.json();
}

export async function getRoute(destination: string) {
  const response = await fetch(`${API_BASE}/routes/${destination}`, {
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch route: ${response.status}`);
  }

  return response.json();
}

export async function getMetrics() {
  const response = await fetch(`${API_BASE}/metrics`, {
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch metrics: ${response.status}`);
  }

  return response.json();
}

export async function getEvents() {
  const response = await fetch(`${API_BASE}/events`, {
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch events: ${response.status}`);
  }

  return response.json();
}

export async function killNode(nodeId: string) {
  const response = await fetch(
    `${API_BASE}/network/simulate/node/${nodeId}/kill`,
    {
      method: 'POST',
    },
  );

  if (!response.ok) {
    throw new Error(`Failed to kill node: ${response.status}`);
  }

  return response.json();
}

export async function restoreNode(nodeId: string) {
  const response = await fetch(
    `${API_BASE}/network/simulate/node/${nodeId}/restore`,
    {
      method: 'POST',
    },
  );

  if (!response.ok) {
    throw new Error(`Failed to restore node: ${response.status}`);
  }

  return response.json();
}

export async function toggleInternet(online: boolean) {
  const endpoint = online
    ? '/network/simulate/connect'
    : '/network/simulate/disconnect';

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to change internet state: ${response.status}`);
  }

  return response.json();
}

export async function resetNetwork() {
  const response = await fetch(`${API_BASE}/network/reset`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to reset network: ${response.status}`);
  }

  return response.json();
}

export async function sendMessage(
  source: string,
  destination: string,
  payload: string,
) {
  const response = await fetch(`${API_BASE}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      source,
      destination,
      payload,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to send message: ${response.status}`);
  }

  return response.json();
}

export function getWebSocketUrl() {
  const httpBase =
    process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';

  return httpBase.replace(/^http/, 'ws') + '/ws/network';
}