'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { MeshNode, MeshLink, NetworkLog, NetworkMetrics } from '@/types/network';

const INITIAL_NODES: MeshNode[] = [
  { id: 'NODE_A', label: 'Node A (Origin)', status: 'ONLINE', ip: '10.0.0.1', latencyMs: 12, storedPacketsCount: 0, x: 14, y: 50 },
  { id: 'NODE_B', label: 'Node B (Relay 1)', status: 'ONLINE', ip: '10.0.0.2', latencyMs: 18, storedPacketsCount: 0, x: 32, y: 25 },
  { id: 'NODE_C', label: 'Node C (Relay 2)', status: 'ONLINE', ip: '10.0.0.3', latencyMs: 22, storedPacketsCount: 0, x: 50, y: 25 },
  { id: 'NODE_D', label: 'Node D (Relay 3)', status: 'ONLINE', ip: '10.0.0.4', latencyMs: 15, storedPacketsCount: 0, x: 68, y: 65 },
  { id: 'NODE_E', label: 'Node E (Target)', status: 'ONLINE', ip: '10.0.0.5', latencyMs: 25, storedPacketsCount: 0, x: 86, y: 50 },
];

const INITIAL_LINKS: MeshLink[] = [
  { source: 'NODE_A', target: 'NODE_B', active: true, quality: 98 },
  { source: 'NODE_B', target: 'NODE_C', active: true, quality: 95 },
  { source: 'NODE_C', target: 'NODE_D', active: true, quality: 91 },
  { source: 'NODE_D', target: 'NODE_E', active: true, quality: 99 },
  { source: 'NODE_B', target: 'NODE_D', active: false, quality: 78 },
];

export function useNetworkState() {
  const [nodes, setNodes] = useState<MeshNode[]>(INITIAL_NODES);
  const [links, setLinks] = useState<MeshLink[]>(INITIAL_LINKS);
  const [activeRoute, setActiveRoute] = useState<string[]>(['NODE_A', 'NODE_B', 'NODE_C', 'NODE_D', 'NODE_E']);
  const [internetOnline, setInternetOnline] = useState<boolean>(true);
  const [logs, setLogs] = useState<NetworkLog[]>([
    { id: '1', timestamp: new Date().toLocaleTimeString(), level: 'INFO', message: 'OFFGRID Core initializing P2P discovery...' },
    { id: '2', timestamp: new Date().toLocaleTimeString(), level: 'SUCCESS', message: 'Optimal path resolved: A → B → C → D → E' }
  ]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const addLog = useCallback((message: string, level: NetworkLog['level'], nodeId?: string) => {
    const newLog: NetworkLog = {
      id: Math.random().toString(),
      timestamp: new Date().toLocaleTimeString(),
      level,
      message,
      nodeId
    };
    setLogs(prev => [newLog, ...prev.slice(0, 49)]);
  }, []);

  const toggleInternet = useCallback(() => {
    setInternetOnline(prev => {
      const nextState = !prev;
      addLog(
        nextState ? 'WAN Gateway online. Synchronizing cloud metrics.' : 'WAN Connection severed. Switching to OFFGRID P2P fallback.',
        nextState ? 'SUCCESS' : 'WARN'
      );
      return nextState;
    });
  }, [addLog]);

  const triggerNodeCFailure = useCallback(() => {
    setNodes(prev => {
      const nodeC = prev.find(n => n.id === 'NODE_C');
      if (nodeC?.status === 'OFFLINE') return prev;

      addLog('UDP Heartbeat timeout on NODE_C.', 'ERROR', 'NODE_C');

      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        addLog('Node failure detected. Recalculating mesh route via Node B...', 'WARN');
        
        setLinks(currLinks => currLinks.map(link => {
          if (link.source === 'NODE_B' && link.target === 'NODE_C') return { ...link, active: false };
          if (link.source === 'NODE_C' && link.target === 'NODE_D') return { ...link, active: false };
          if (link.source === 'NODE_B' && link.target === 'NODE_D') return { ...link, active: true };
          return link;
        }));

        setActiveRoute(['NODE_A', 'NODE_B', 'NODE_D', 'NODE_E']);
        addLog('Self-healing complete. Rerouted path: A → B → D → E', 'SUCCESS');
      }, 1000);

      return prev.map(node => 
        node.id === 'NODE_C' ? { ...node, status: 'OFFLINE', latencyMs: 0 } : node
      );
    });
  }, [addLog]);

  const resetNetwork = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setNodes(INITIAL_NODES);
    setLinks(INITIAL_LINKS);
    setActiveRoute(['NODE_A', 'NODE_B', 'NODE_C', 'NODE_D', 'NODE_E']);
    setInternetOnline(true);
    addLog('Network topology reset to initial state.', 'INFO');
  }, [addLog]);

  const activeNodesList = nodes.filter(n => n.status !== 'OFFLINE');
  const avgMeshLatencyMs = activeNodesList.length > 0
    ? Math.round(activeNodesList.reduce((acc, n) => acc + n.latencyMs, 0) / activeNodesList.length)
    : 0;

  const metrics: NetworkMetrics = {
    totalNodes: nodes.length,
    activeNodes: activeNodesList.length,
    activePathHops: activeRoute,
    internetAvailable: internetOnline,
    storeAndForwardQueueSize: nodes.reduce((acc, n) => acc + n.storedPacketsCount, 0),
    avgMeshLatencyMs
  };

  return { nodes, links, activeRoute, internetOnline, logs, metrics, actions: { toggleInternet, triggerNodeCFailure, resetNetwork } };
}