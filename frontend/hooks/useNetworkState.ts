'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { MeshNode, MeshLink, NetworkLog, NetworkMetrics, TransferState } from '@/types/network';
import {
  RealNodeSnapshot,
  RealNodeSnapshotLog,
  fetchSnapshot,
  fetchLiveState,
  sendRealMessage,
  LiveStateMessage,
} from '@/lib/realNodeApi';

/** Lifecycle row for a message this dashboard sent or received. */
export interface MessageTrackedEvent {
  id: string;
  source: string;
  destination: string;
  text: string;
  status: 'PENDING' | 'FORWARDED' | 'DELIVERED' | 'FAILED' | 'RECEIVED';
  timestamp: string;
  hopCount?: number;
}

const INITIAL_NODES: MeshNode[] = [
  { id: 'NODE_A', label: 'Node A (Origin)', status: 'ONLINE', ip: '10.0.0.1', latencyMs: 12, storedPacketsCount: 0, x: 14, y: 50, neighbors: ['Node B'], lastSeenMs: 1 },
  { id: 'NODE_B', label: 'Node B (Relay 1)', status: 'ONLINE', ip: '10.0.0.2', latencyMs: 18, storedPacketsCount: 0, x: 32, y: 25, neighbors: ['Node A', 'Node C', 'Node D'], lastSeenMs: 2 },
  { id: 'NODE_C', label: 'Node C (Relay 2)', status: 'ONLINE', ip: '10.0.0.3', latencyMs: 22, storedPacketsCount: 0, x: 50, y: 25, neighbors: ['Node B', 'Node D'], lastSeenMs: 2 },
  { id: 'NODE_D', label: 'Node D (Relay 3)', status: 'ONLINE', ip: '10.0.0.4', latencyMs: 15, storedPacketsCount: 0, x: 68, y: 65, neighbors: ['Node B', 'Node C', 'Node E'], lastSeenMs: 3 },
  { id: 'NODE_E', label: 'Node E (Target)', status: 'ONLINE', ip: '10.0.0.5', latencyMs: 25, storedPacketsCount: 0, x: 86, y: 50, neighbors: ['Node D'], lastSeenMs: 2 },
];

const INITIAL_LINKS: MeshLink[] = [
  { source: 'NODE_A', target: 'NODE_B', active: true, quality: 98 },
  { source: 'NODE_B', target: 'NODE_C', active: true, quality: 95 },
  { source: 'NODE_C', target: 'NODE_D', active: true, quality: 91 },
  { source: 'NODE_D', target: 'NODE_E', active: true, quality: 99 },
  { source: 'NODE_B', target: 'NODE_D', active: false, quality: 78 },
];

const formatTimestamp = (date: Date = new Date()) => {
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
};

const INITIAL_LOGS: NetworkLog[] = [
  { id: '1', timestamp: '12:00:00', level: 'INFO', message: 'OFFGRID Core initializing P2P discovery...' },
  { id: '2', timestamp: '12:00:01', level: 'SUCCESS', message: 'Optimal path resolved: A → B → C → D → E' }
];

/** API base of the real node this dashboard should mirror, if any. */
function resolveRealNodeUrl(): string | null {
  if (typeof window === 'undefined') return null;
  const url = process.env.NEXT_PUBLIC_OFFGRID_API?.trim();
  return url ? url.replace(/\/$/, '') : null;
}

export function useNetworkState() {
  const realNodeUrlRef = useRef<string | null>(null);
  if (realNodeUrlRef.current === null) {
    realNodeUrlRef.current = resolveRealNodeUrl();
  }

  const [nodes, setNodes] = useState<MeshNode[]>(INITIAL_NODES);
  const [links, setLinks] = useState<MeshLink[]>(INITIAL_LINKS);
  const [activeRoute, setActiveRoute] = useState<string[]>(['NODE_A', 'NODE_B', 'NODE_C', 'NODE_D', 'NODE_E']);
  const [selectedNodeId, setSelectedNodeId] = useState<string>('NODE_C');
  const [internetOnline, setInternetOnline] = useState<boolean>(false); // Starts OFF as per wireframe: Internet: OFF (Amber)
  const [logs, setLogs] = useState<NetworkLog[]>(INITIAL_LOGS);
  const [liveMode, setLiveMode] = useState<boolean>(false);
  const [sendingMessage, setSendingMessage] = useState<boolean>(false);
  const [messageEvents, setMessageEvents] = useState<MessageTrackedEvent[]>([]);
  const prevStatusesRef = useRef<Map<string, string>>(new Map());
  const prevNodeStatesRef = useRef<Map<string, string>>(new Map());
  const seenInboxRef = useRef<Set<string>>(new Set());
  const [transferState, setTransferState] = useState<TransferState>({
    isTransferring: false,
    transferType: null,
    transferProgress: 100,
    messageQueue: 0
  });

  const transferIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      if (transferIntervalRef.current) clearInterval(transferIntervalRef.current);
    };
  }, []);

  const upsertMessageEvent = useCallback((event: MessageTrackedEvent) => {
    setMessageEvents(prev => {
      const next = prev.filter(e => e.id !== event.id);
      next.unshift(event);
      return next.slice(0, 30);
    });
  }, []);

  const addLog = useCallback((message: string, level: NetworkLog['level'], nodeId?: string) => {
    const newLog: NetworkLog = {
      id: Math.random().toString(),
      timestamp: formatTimestamp(),
      level,
      message,
      nodeId
    };
    setLogs(prev => [newLog, ...prev.slice(0, 49)]);
  }, []);

  // ------------------------------------------------------------------
  // REAL LAN MODE: poll the local node's FastAPI and mirror its state.
  // ------------------------------------------------------------------
  useEffect(() => {
    const baseUrl = realNodeUrlRef.current;
    if (!baseUrl) return;

    let cancelled = false;

    const poll = async () => {
      try {
        const snap: RealNodeSnapshot = await fetchSnapshot(baseUrl);
        if (cancelled) return;

        setNodes(
          snap.nodes.map(n => ({
            ...n,
            label: n.label || n.id,
            latencyMs: n.status === 'ONLINE' ? n.latencyMs || 15 : 0,
          }))
        );
        setLinks(
          snap.links.map(l => ({
            source: l.source,
            target: l.target,
            active: l.active,
            quality: Math.round((l.quality ?? 0) * 100),
          }))
        );
        setActiveRoute(snap.activeRoute || []);
        setInternetOnline(false);
        setLiveMode(true);

        if (snap.logs?.length) {
          const mapped: NetworkLog[] = snap.logs.map((log: RealNodeSnapshotLog) => ({
            id: log.id,
            timestamp: formatTimestamp(new Date(log.timestamp)),
            level: (['INFO', 'WARN', 'ERROR', 'SUCCESS'].includes(log.level) ? log.level : 'INFO') as NetworkLog['level'],
            message: log.message,
            nodeId: log.nodeId ?? undefined,
          }));
          setLogs(mapped.reverse());
        }
      } catch {
        if (!cancelled) setLiveMode(false);
      }
    };

    poll();
    const interval = setInterval(poll, 1500);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // ------------------------------------------------------------------
  // REAL-TIME STATE: node activations + message lifecycle.
  // Polls GET /state (lightweight) at high frequency and diffs it
  // locally to produce events:
  //   "NODE_B activated (ONLINE)" / "NODE_C went OFFLINE"
  //   "Message to NODE_B: PENDING -> FORWARDED -> DELIVERED"
  //   "Message received from NODE_A: 'Hello'"
  // ------------------------------------------------------------------
  useEffect(() => {
    const baseUrl = realNodeUrlRef.current;
    if (!baseUrl) return;

    let cancelled = false;
    let firstPoll = true;

    const statusToEventLevel = (s: string): NetworkLog['level'] =>
      s === 'ONLINE' ? 'SUCCESS' : 'ERROR';

    const pollState = async () => {
      try {
        const state = await fetchLiveState(baseUrl);
        if (cancelled) return;

        setLiveMode(true);

        // ---- Node activation diff --------------------------------
        const prevNodes = prevNodeStatesRef.current;

        for (const n of state.nodes) {
          const before = prevNodes.get(n.id);

          if (before !== n.status) {
            prevNodes.set(n.id, n.status);

            if (!firstPoll) {
              if (n.status === 'ONLINE') {
                addLog(`${n.id} ACTIVATED — heartbeat link established`, 'SUCCESS', n.id);
              } else {
                addLog(`${n.id} went OFFLINE — heartbeat lost`, 'ERROR', n.id);
              }
            }
          }
        }

        // ---- Message lifecycle diff ------------------------------
        const prevStatuses = prevStatusesRef.current;
        const now = new Date();

        for (const m of state.messages ?? []) {
          const id = m.message_id ?? m.messageId ?? '';
          if (!id) continue;

          const before = prevStatuses.get(id);
          const current = m.status as MessageTrackedEvent['status'];

          if (before !== current) {
            prevStatuses.set(id, current);

            upsertMessageEvent({
              id,
              source: m.source,
              destination: m.destination,
              text: m.payload ?? m.text ?? '',
              status: (['PENDING', 'FORWARDED', 'DELIVERED', 'FAILED'].includes(current)
                ? current
                : 'PENDING') as MessageTrackedEvent['status'],
              timestamp: formatTimestamp(now),
            });

            if (!firstPoll) {
              if (current === 'DELIVERED') {
                addLog(`ACK received — message to ${m.destination} DELIVERED ✓`, 'SUCCESS', m.destination);
              } else if (current === 'FORWARDED') {
                addLog(`Message to ${m.destination} transmitted over UDP mesh`, 'INFO', m.destination);
              } else if (current === 'PENDING') {
                addLog(`Message to ${m.destination} queued (destination unreachable)`, 'WARN', m.destination);
              }
            }
          }
        }

        // ---- Received messages (this node's inbox) ---------------
        for (const item of state.inbox ?? []) {
          if (seenInboxRef.current.has(item.message_id)) continue;

          seenInboxRef.current.add(item.message_id);

          upsertMessageEvent({
            id: item.message_id,
            source: item.source,
            destination: item.destination,
            text: item.text,
            status: 'RECEIVED',
            timestamp: formatTimestamp(new Date(item.received_at * 1000)),
            hopCount: item.hop_count,
          });

          if (!firstPoll) {
            addLog(
              `Message RECEIVED from ${item.source}: "${item.text}" (hops=${item.hop_count})`,
              'SUCCESS',
              item.source
            );
          }
        }

        firstPoll = false;
      } catch {
        // node unreachable — liveMode flips back via the topology poll
      }
    };

    pollState();
    const interval = setInterval(pollState, 1000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [addLog, upsertMessageEvent]);

  const sendMessageToNode = useCallback(
    async (destination: string, payload: string): Promise<boolean> => {
      const baseUrl = realNodeUrlRef.current;
      if (!baseUrl) {
        addLog('Live node API not configured (NEXT_PUBLIC_OFFGRID_API).', 'ERROR');
        return false;
      }

      setSendingMessage(true);
      try {
        const result = await sendRealMessage(baseUrl, destination, payload);
        addLog(
          `Message to ${destination}: ${result.status} (route: ${result.route?.join(' → ') || 'flooding'})`,
          result.status === 'FORWARDED' ? 'SUCCESS' : 'WARN'
        );
        return result.status === 'FORWARDED';
      } catch (error) {
        addLog(`Send failed: ${error instanceof Error ? error.message : 'unknown error'}`, 'ERROR');
        return false;
      } finally {
        setSendingMessage(false);
      }
    },
    [addLog]
  );

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

  const killNode = useCallback((nodeId: 'NODE_C' | 'NODE_E') => {
    setNodes(prev => {
      const targetNode = prev.find(n => n.id === nodeId);
      if (targetNode?.status === 'OFFLINE') return prev;

      addLog(`${targetNode?.label || nodeId} offline. Connection lost.`, 'ERROR', nodeId);

      if (nodeId === 'NODE_C') {
        setTimeout(() => {
          setLinks(currLinks => currLinks.map(link => {
            if (link.source === 'NODE_B' && link.target === 'NODE_C') return { ...link, active: false };
            if (link.source === 'NODE_C' && link.target === 'NODE_D') return { ...link, active: false };
            if (link.source === 'NODE_B' && link.target === 'NODE_D') return { ...link, active: true };
            return link;
          }));

          setNodes(latestNodes => {
            const isEOffline = latestNodes.find(n => n.id === 'NODE_E')?.status === 'OFFLINE';
            const newRoute = isEOffline 
              ? ['NODE_A', 'NODE_B', 'NODE_D'] 
              : ['NODE_A', 'NODE_B', 'NODE_D', 'NODE_E'];
            setActiveRoute(newRoute);
            addLog(`Route recalculated: ${newRoute.map(id => id.replace('NODE_', '')).join(' → ')}`, 'WARN');
            return latestNodes;
          });
        }, 300);
      } else if (nodeId === 'NODE_E') {
        setTimeout(() => {
          setLinks(currLinks => currLinks.map(link => {
            if (link.source === 'NODE_D' && link.target === 'NODE_E') return { ...link, active: false };
            return link;
          }));

          setNodes(latestNodes => {
            const isCOffline = latestNodes.find(n => n.id === 'NODE_C')?.status === 'OFFLINE';
            const newRoute = isCOffline 
              ? ['NODE_A', 'NODE_B', 'NODE_D'] 
              : ['NODE_A', 'NODE_B', 'NODE_C', 'NODE_D'];
            setActiveRoute(newRoute);
            addLog(`Target Node E unreachable. Route truncated at Node D. Store-and-Forward queue active.`, 'WARN');
            return latestNodes;
          });
        }, 300);
      }

      return prev.map(node => 
        node.id === nodeId ? { ...node, status: 'OFFLINE', latencyMs: 0 } : node
      );
    });
  }, [addLog]);

  const restoreNode = useCallback((nodeId: 'NODE_C' | 'NODE_E') => {
    setNodes(prev => {
      const targetNode = prev.find(n => n.id === nodeId);
      if (targetNode?.status === 'ONLINE') return prev;

      addLog(`${targetNode?.label || nodeId} restored. Re-establishing link heartbeats...`, 'SUCCESS', nodeId);

      if (nodeId === 'NODE_C') {
        setLinks(currLinks => currLinks.map(link => {
          if (link.source === 'NODE_B' && link.target === 'NODE_C') return { ...link, active: true };
          if (link.source === 'NODE_C' && link.target === 'NODE_D') return { ...link, active: true };
          if (link.source === 'NODE_B' && link.target === 'NODE_D') return { ...link, active: false };
          return link;
        }));

        setNodes(latestNodes => {
          const isEOffline = latestNodes.find(n => n.id === 'NODE_E')?.status === 'OFFLINE';
          const newRoute = isEOffline 
            ? ['NODE_A', 'NODE_B', 'NODE_C', 'NODE_D'] 
            : ['NODE_A', 'NODE_B', 'NODE_C', 'NODE_D', 'NODE_E'];
          setActiveRoute(newRoute);
          addLog(`Route restored to optimal path: ${newRoute.map(id => id.replace('NODE_', '')).join(' → ')}`, 'SUCCESS');
          return latestNodes;
        });
      } else if (nodeId === 'NODE_E') {
        setLinks(currLinks => currLinks.map(link => {
          if (link.source === 'NODE_D' && link.target === 'NODE_E') return { ...link, active: true };
          return link;
        }));

        setNodes(latestNodes => {
          const isCOffline = latestNodes.find(n => n.id === 'NODE_C')?.status === 'OFFLINE';
          const newRoute = isCOffline 
            ? ['NODE_A', 'NODE_B', 'NODE_D', 'NODE_E'] 
            : ['NODE_A', 'NODE_B', 'NODE_C', 'NODE_D', 'NODE_E'];
          setActiveRoute(newRoute);

          // Flush stored packets if Node D had buffered anything
          const nodeD = latestNodes.find(n => n.id === 'NODE_D');
          if (nodeD && nodeD.storedPacketsCount > 0) {
            addLog(`Flushing ${nodeD.storedPacketsCount} stored packet(s) from Node D buffer to Node E.`, 'SUCCESS');
          }
          addLog(`Route extended to Target Node E: ${newRoute.map(id => id.replace('NODE_', '')).join(' → ')}`, 'SUCCESS');

          return latestNodes.map(n => n.id === 'NODE_D' ? { ...n, storedPacketsCount: 0 } : n);
        });
      }

      const defaultLatency = nodeId === 'NODE_C' ? 22 : 25;
      return prev.map(node => 
        node.id === nodeId ? { ...node, status: 'ONLINE', latencyMs: defaultLatency } : node
      );
    });
  }, [addLog]);

  const sendTransfer = useCallback((type: 'MESSAGE' | 'FILE') => {
    if (transferState.isTransferring) {
      setTransferState(prev => ({ ...prev, messageQueue: prev.messageQueue + 1 }));
      addLog(`Transfer in flight. Queued additional ${type.toLowerCase()} for relay.`, 'INFO');
      return;
    }

    addLog(`Initiating P2P ${type === 'FILE' ? 'chunked binary transfer' : 'telemetry payload'} from Node A...`, 'INFO');
    setTransferState(prev => ({
      ...prev,
      isTransferring: true,
      transferType: type,
      transferProgress: 0
    }));

    if (transferIntervalRef.current) clearInterval(transferIntervalRef.current);

    let progress = 0;
    transferIntervalRef.current = setInterval(() => {
      progress += 20;
      if (progress === 40) {
        setNodes(currNodes => {
          const isCOffline = currNodes.find(n => n.id === 'NODE_C')?.status === 'OFFLINE';
          if (isCOffline) {
            addLog('Message forwarded via fallback hop: Node B → Node D', 'INFO');
          } else {
            addLog('Packet relayed through Node B → Node C', 'INFO');
          }
          return currNodes;
        });
      }

      if (progress >= 100) {
        if (transferIntervalRef.current) clearInterval(transferIntervalRef.current);
        setTransferState(prev => ({
          isTransferring: false,
          transferType: null,
          transferProgress: 100,
          messageQueue: Math.max(0, prev.messageQueue - 1)
        }));

        setNodes(currNodes => {
          const isEOffline = currNodes.find(n => n.id === 'NODE_E')?.status === 'OFFLINE';
          if (isEOffline) {
            addLog(`Target Node E offline. Payload saved to Node D Store-and-Forward queue.`, 'WARN');
            return currNodes.map(n => n.id === 'NODE_D' ? { ...n, storedPacketsCount: n.storedPacketsCount + 1 } : n);
          } else {
            addLog(`Payload delivered successfully to Node E (Target). Transfer verified.`, 'SUCCESS');
            return currNodes;
          }
        });
      } else {
        setTransferState(prev => ({ ...prev, transferProgress: progress }));
      }
    }, 200);
  }, [addLog, transferState.isTransferring]);

  const resetNetwork = useCallback(() => {
    if (transferIntervalRef.current) {
      clearInterval(transferIntervalRef.current);
      transferIntervalRef.current = null;
    }
    setNodes(INITIAL_NODES);
    setLinks(INITIAL_LINKS);
    setActiveRoute(['NODE_A', 'NODE_B', 'NODE_C', 'NODE_D', 'NODE_E']);
    setInternetOnline(false);
    setSelectedNodeId('NODE_C');
    setTransferState({
      isTransferring: false,
      transferType: null,
      transferProgress: 100,
      messageQueue: 0
    });
    addLog('Network topology reset to initial state.', 'INFO');
  }, [addLog]);

  const activeNodesList = nodes.filter(n => n.status !== 'OFFLINE');
  const activeLinksCount = links.filter(l => l.active).length;
  const avgMeshLatencyMs = activeNodesList.length > 0
    ? Math.round(activeNodesList.reduce((acc, n) => acc + n.latencyMs, 0) / activeNodesList.length)
    : 0;

  const metrics: NetworkMetrics = {
    totalNodes: nodes.length,
    activeNodes: activeNodesList.length,
    activeLinksCount,
    activePathHops: activeRoute,
    internetAvailable: internetOnline,
    storeAndForwardQueueSize: nodes.reduce((acc, n) => acc + n.storedPacketsCount, 0),
    avgMeshLatencyMs
  };

  const selectedNode = nodes.find(n => n.id === selectedNodeId) || nodes[0];

  return {
    nodes,
    links,
    activeRoute,
    selectedNode,
    setSelectedNodeId,
    internetOnline,
    logs,
    metrics,
    transferState,
    liveMode,
    sendingMessage,
    sendMessageToNode,
    messageEvents,
    actions: {
      toggleInternet,
      killNode,
      restoreNode,
      sendTransfer,
      resetNetwork
    }
  };
}
