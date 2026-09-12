export type NodeStatus = 'ONLINE' | 'DEGRADED' | 'OFFLINE';

export interface MeshNode {
  id: string;
  label: string;
  status: NodeStatus;
  ip: string;
  latencyMs: number;
  storedPacketsCount: number;
  x: number;
  y: number;
}

export interface MeshLink {
  source: string;
  target: string;
  active: boolean;
  quality: number;
}

export interface NetworkLog {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS';
  message: string;
  nodeId?: string;
}

export interface NetworkMetrics {
  totalNodes: number;
  activeNodes: number;
  activePathHops: string[];
  internetAvailable: boolean;
  storeAndForwardQueueSize: number;
  avgMeshLatencyMs: number;
}
