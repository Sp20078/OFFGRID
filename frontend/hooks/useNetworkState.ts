'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  getEvents,
  getMetrics,
  getNodes,
  getRoute,
  getTopology,
  getWebSocketUrl,
  killNode as apiKillNode,
  resetNetwork as apiResetNetwork,
  restoreNode as apiRestoreNode,
  sendMessage,
  toggleInternet as apiToggleInternet,
} from '@/lib/api';

import {
  MeshLink,
  MeshNode,
  NetworkLog,
  NetworkMetrics,
  TransferState,
} from '@/types/network';

type NetworkSnapshot = {
  nodes: MeshNode[];
  links: MeshLink[];
  activeRoute?: string[];
  metrics: NetworkMetrics;
  logs: NetworkLog[];
  internetOnline: boolean;
};

type TopologyResponse = {
  nodes: MeshNode[];
  links: MeshLink[];
  activeRoute?: string[];
};

type RouteResponse = {
  route?: string[];
};

const DEFAULT_SELECTED_NODE = 'NODE_C';

const EMPTY_METRICS: NetworkMetrics = {
  totalNodes: 0,
  activeNodes: 0,
  activeLinksCount: 0,
  activePathHops: [],
  internetAvailable: false,
  storeAndForwardQueueSize: 0,
  avgMeshLatencyMs: 0,
};

const EMPTY_TRANSFER_STATE: TransferState = {
  isTransferring: false,
  transferType: null,
  transferProgress: 100,
  messageQueue: 0,
};

export function useNetworkState() {
  const [nodes, setNodes] = useState<MeshNode[]>([]);
  const [links, setLinks] = useState<MeshLink[]>([]);
  const [activeRoute, setActiveRoute] = useState<string[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState(
    DEFAULT_SELECTED_NODE,
  );
  const [internetOnline, setInternetOnline] = useState(false);
  const [logs, setLogs] = useState<NetworkLog[]>([]);
  const [metrics, setMetrics] =
    useState<NetworkMetrics>(EMPTY_METRICS);

  const [transferState, setTransferState] =
    useState<TransferState>(EMPTY_TRANSFER_STATE);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const websocketRef = useRef<WebSocket | null>(null);

  const applySnapshot = useCallback(
    (snapshot: NetworkSnapshot) => {
      const safeNodes = snapshot.nodes ?? [];
      const safeLinks = snapshot.links ?? [];

      const route =
        snapshot.activeRoute ??
        snapshot.metrics?.activePathHops ??
        [];

      const safeMetrics: NetworkMetrics =
        snapshot.metrics ?? {
          ...EMPTY_METRICS,
          totalNodes: safeNodes.length,
          activeNodes: safeNodes.filter(
            (node) => node.status !== 'OFFLINE',
          ).length,
          activeLinksCount: safeLinks.filter(
            (link) => link.active,
          ).length,
          activePathHops: route,
          internetAvailable:
            snapshot.internetOnline ?? false,
        };

      setNodes(safeNodes);
      setLinks(safeLinks);
      setActiveRoute(route);
      setMetrics({
        ...safeMetrics,
        activePathHops: route,
      });
      setLogs(snapshot.logs ?? []);
      setInternetOnline(snapshot.internetOnline ?? false);

      setSelectedNodeId((current) => {
        if (
          current &&
          safeNodes.some((node) => node.id === current)
        ) {
          return current;
        }

        return safeNodes[0]?.id ?? DEFAULT_SELECTED_NODE;
      });
    },
    [],
  );

  const refreshNetwork = useCallback(async () => {
    try {
      setError(null);

      const [
        nodesResponse,
        topologyResponse,
        metricsResponse,
        eventsResponse,
        routeResponse,
      ] = await Promise.all([
        getNodes(),
        getTopology() as Promise<TopologyResponse>,
        getMetrics() as Promise<NetworkMetrics>,
        getEvents() as Promise<NetworkLog[]>,
        getRoute('NODE_E') as Promise<RouteResponse>,
      ]);

      const route =
        routeResponse?.route ??
        topologyResponse?.activeRoute ??
        metricsResponse?.activePathHops ??
        [];

      applySnapshot({
        nodes: nodesResponse ?? [],
        links: topologyResponse?.links ?? [],
        activeRoute: route,
        metrics: {
          ...EMPTY_METRICS,
          ...(metricsResponse ?? {}),
          activePathHops: route,
        },
        logs: eventsResponse ?? [],
        internetOnline:
          metricsResponse?.internetAvailable ?? false,
      });
    } catch (err) {
      console.error(
        'Failed to refresh OFFGRID state:',
        err,
      );

      setError(
        err instanceof Error
          ? err.message
          : 'Failed to connect to OFFGRID backend',
      );
    } finally {
      setLoading(false);
    }
  }, [applySnapshot]);

  useEffect(() => {
    void refreshNetwork();
  }, [refreshNetwork]);

  useEffect(() => {
    let socket: WebSocket | null = null;

    try {
      socket = new WebSocket(getWebSocketUrl());
      websocketRef.current = socket;

      socket.onopen = () => {
        console.log('OFFGRID WebSocket connected');
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          if (
            message?.type === 'NETWORK_STATE' &&
            message?.data
          ) {
            applySnapshot(message.data);
          }
        } catch (err) {
          console.error(
            'Invalid OFFGRID WebSocket message:',
            err,
          );
        }
      };

      socket.onerror = (event) => {
        console.warn(
          'OFFGRID WebSocket error:',
          event,
        );
      };

      socket.onclose = () => {
        websocketRef.current = null;
      };
    } catch (err) {
      console.error(
        'Unable to open OFFGRID WebSocket:',
        err,
      );
    }

    return () => {
      socket?.close();
      websocketRef.current = null;
    };
  }, [applySnapshot]);

  const toggleInternet = useCallback(async () => {
    try {
      setError(null);

      const nextState = !internetOnline;

      const snapshot = await apiToggleInternet(
        nextState,
      );

      applySnapshot({
        nodes: snapshot?.nodes ?? nodes,
        links: snapshot?.links ?? links,
        activeRoute: snapshot?.activeRoute ?? activeRoute,
        metrics:
          snapshot?.metrics ?? {
            ...metrics,
            internetAvailable: nextState,
          },
        logs: snapshot?.logs ?? logs,
        internetOnline:
          snapshot?.internetOnline ?? nextState,
      });
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : 'Failed to change internet state',
      );

      await refreshNetwork();
    }
  }, [
    activeRoute,
    applySnapshot,
    internetOnline,
    links,
    logs,
    metrics,
    nodes,
    refreshNetwork,
  ]);

  const killNode = useCallback(
    async (nodeId: 'NODE_C' | 'NODE_E') => {
      try {
        setError(null);

        const snapshot = await apiKillNode(nodeId);

        applySnapshot({
          nodes: snapshot?.nodes ?? nodes,
          links: snapshot?.links ?? links,
          activeRoute:
            snapshot?.activeRoute ??
            snapshot?.metrics?.activePathHops ??
            [],
          metrics: snapshot?.metrics ?? metrics,
          logs: snapshot?.logs ?? logs,
          internetOnline:
            snapshot?.internetOnline ?? internetOnline,
        });
      } catch (err) {
        console.error(err);

        setError(
          err instanceof Error
            ? err.message
            : 'Failed to kill node',
        );

        await refreshNetwork();
      }
    },
    [
      applySnapshot,
      internetOnline,
      links,
      logs,
      metrics,
      nodes,
      refreshNetwork,
    ],
  );

  const restoreNode = useCallback(
    async (nodeId: 'NODE_C' | 'NODE_E') => {
      try {
        setError(null);

        const snapshot =
          await apiRestoreNode(nodeId);

        applySnapshot({
          nodes: snapshot?.nodes ?? nodes,
          links: snapshot?.links ?? links,
          activeRoute:
            snapshot?.activeRoute ??
            snapshot?.metrics?.activePathHops ??
            [],
          metrics: snapshot?.metrics ?? metrics,
          logs: snapshot?.logs ?? logs,
          internetOnline:
            snapshot?.internetOnline ?? internetOnline,
        });
      } catch (err) {
        console.error(err);

        setError(
          err instanceof Error
            ? err.message
            : 'Failed to restore node',
        );

        await refreshNetwork();
      }
    },
    [
      applySnapshot,
      internetOnline,
      links,
      logs,
      metrics,
      nodes,
      refreshNetwork,
    ],
  );

  const sendTransfer = useCallback(
    async (type: 'MESSAGE' | 'FILE') => {
      if (transferState.isTransferring) {
        setTransferState((previous) => ({
          ...previous,
          messageQueue:
            previous.messageQueue + 1,
        }));

        return;
      }

      if (type === 'FILE') {
        setError(
          'File transfer backend integration is not connected yet.',
        );
        return;
      }

      try {
        setError(null);

        setTransferState({
          isTransferring: true,
          transferType: 'MESSAGE',
          transferProgress: 10,
          messageQueue: 0,
        });

        const result = await sendMessage(
          'NODE_A',
          'NODE_E',
          'Emergency evacuation at Block B.',
        );

        const returnedRoute =
          result?.route ?? [];

        setActiveRoute(returnedRoute);

        await refreshNetwork();

        if (result?.status === 'PENDING') {
          setTransferState({
            isTransferring: false,
            transferType: null,
            transferProgress: 0,
            messageQueue: 1,
          });

          setError(
            'Node E is offline. Message stored locally and waiting for destination.',
          );

          return;
        }

        if (result?.status !== 'DELIVERED') {
          setTransferState({
            isTransferring: false,
            transferType: null,
            transferProgress: 0,
            messageQueue: 0,
          });

          setError(
            'Message was not delivered.',
          );

          return;
        }

        setTransferState({
          isTransferring: false,
          transferType: null,
          transferProgress: 100,
          messageQueue: 0,
        });
      } catch (err) {
        console.error(err);

        setTransferState({
          isTransferring: false,
          transferType: null,
          transferProgress: 0,
          messageQueue: 0,
        });

        setError(
          err instanceof Error
            ? err.message
            : 'Failed to send message',
        );
      }
    },
    [
      refreshNetwork,
      transferState.isTransferring,
    ],
  );

  const resetNetwork = useCallback(async () => {
    try {
      setError(null);

      const snapshot =
        await apiResetNetwork();

      setTransferState(
        EMPTY_TRANSFER_STATE,
      );

      applySnapshot({
        nodes: snapshot?.nodes ?? [],
        links: snapshot?.links ?? [],
        activeRoute:
          snapshot?.activeRoute ??
          snapshot?.metrics?.activePathHops ??
          [],
        metrics:
          snapshot?.metrics ?? EMPTY_METRICS,
        logs: snapshot?.logs ?? [],
        internetOnline:
          snapshot?.internetOnline ?? false,
      });
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : 'Failed to reset network',
      );

      await refreshNetwork();
    }
  }, [applySnapshot, refreshNetwork]);

  const selectedNode =
    nodes.find(
      (node) => node.id === selectedNodeId,
    ) ??
    nodes[0] ??
    ({
      id: DEFAULT_SELECTED_NODE,
      label: 'Loading...',
      status: 'OFFLINE',
      ip: '',
      latencyMs: 0,
      storedPacketsCount: 0,
      x: 50,
      y: 50,
      neighbors: [],
      lastSeenMs: 0,
    } satisfies MeshNode);

  return {
    nodes,
    links,
    activeRoute,
    selectedNode,
    selectedNodeId,
    setSelectedNodeId,
    internetOnline,
    logs,
    metrics,
    transferState,
    loading,
    error,

    actions: {
      toggleInternet,
      killNode,
      restoreNode,
      sendTransfer,
      resetNetwork,
      refreshNetwork,
    },
  };
}