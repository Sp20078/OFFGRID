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
  neighbors: string[];
  lastSeenMs: number;
  hardwareInfo?: string;
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
  activeLinksCount: number;
  activePathHops: string[];
  internetAvailable: boolean;
  storeAndForwardQueueSize: number;
  avgMeshLatencyMs: number;
}

export interface TransferState {
  isTransferring: boolean;
  transferType: 'MESSAGE' | 'FILE' | null;
  transferProgress: number;
  messageQueue: number;
}
