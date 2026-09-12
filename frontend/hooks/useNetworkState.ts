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
  nodes?: MeshNode[];
  links?: MeshLink[];
  activeRoute?: string[];
  metrics?: Partial<NetworkMetrics>;
  logs?: NetworkLog[];
  internetOnline?: boolean;
};

type TopologyResponse = {
  nodes?: MeshNode[];
  links?: MeshLink[];
  activeRoute?: string[];
};

type RouteResponse = {
  route?: string[];
};

type ApiActionResponse = NetworkSnapshot & {
  status?: string;
  route?: string[];
  message?: string;
};

const DEFAULT_SELECTED_NODE = 'NODE_A';

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
  transferProgress: 0,
  messageQueue: 0,
};

export function useNetworkState() {
  const [nodes, setNodes] = useState<MeshNode[]>([]);
  const [links, setLinks] = useState<MeshLink[]>([]);
  const [activeRoute, setActiveRoute] = useState<string[]>([]);

  const [selectedNodeId, setSelectedNodeId] =
    useState<string>(DEFAULT_SELECTED_NODE);

  const [internetOnline, setInternetOnline] =
    useState<boolean>(false);

  const [logs, setLogs] = useState<NetworkLog[]>([]);
  const [metrics, setMetrics] =
    useState<NetworkMetrics>(EMPTY_METRICS);

  const [transferState, setTransferState] =
    useState<TransferState>(EMPTY_TRANSFER_STATE);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const websocketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef =
    useRef<ReturnType<typeof setTimeout> | null>(null);

  const stoppedRef = useRef<boolean>(false);
  const connectInProgressRef = useRef<boolean>(false);

  // ---------------------------------------------------------------------------
  // Apply backend snapshot to frontend state
  // ---------------------------------------------------------------------------

  const applySnapshot = useCallback(
    (snapshot: NetworkSnapshot) => {
      const nextNodes = snapshot.nodes ?? [];
      const nextLinks = snapshot.links ?? [];

      const nextRoute =
        snapshot.activeRoute ??
        snapshot.metrics?.activePathHops ??
        [];

      const nextMetrics: NetworkMetrics = {
        ...EMPTY_METRICS,
        ...(snapshot.metrics ?? {}),
        totalNodes:
          snapshot.metrics?.totalNodes ??
          nextNodes.length,
        activeNodes:
          snapshot.metrics?.activeNodes ??
          nextNodes.filter(
            (node) => node.status !== 'OFFLINE',
          ).length,
        activeLinksCount:
          snapshot.metrics?.activeLinksCount ??
          nextLinks.filter(
            (link) => link.active,
          ).length,
        activePathHops: nextRoute,
        internetAvailable:
          snapshot.metrics?.internetAvailable ??
          snapshot.internetOnline ??
          false,
      };

      setNodes(nextNodes);
      setLinks(nextLinks);
      setActiveRoute(nextRoute);
      setMetrics(nextMetrics);
      setLogs(snapshot.logs ?? []);

      setInternetOnline(
        snapshot.internetOnline ??
          nextMetrics.internetAvailable,
      );

      setSelectedNodeId((current) => {
        if (
          nextNodes.some(
            (node) => node.id === current,
          )
        ) {
          return current;
        }

        return (
          nextNodes[0]?.id ??
          DEFAULT_SELECTED_NODE
        );
      });
    },
    [],
  );

  // ---------------------------------------------------------------------------
  // REST refresh
  // ---------------------------------------------------------------------------

  const refreshNetwork = useCallback(async () => {
    try {
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
          metricsResponse?.internetAvailable ??
          false,
      });

      setError(null);
    } catch (err) {
      console.error(
        'OFFGRID REST refresh failed:',
        err,
      );

      setError(
        err instanceof Error
          ? err.message
          : 'Unable to reach OFFGRID backend',
      );
    } finally {
      setLoading(false);
    }
  }, [applySnapshot]);

  // ---------------------------------------------------------------------------
  // Initial load
  // ---------------------------------------------------------------------------

  useEffect(() => {
    void refreshNetwork();
  }, [refreshNetwork]);

  // ---------------------------------------------------------------------------
  // WebSocket
  // ---------------------------------------------------------------------------

  useEffect(() => {
    stoppedRef.current = false;
    connectInProgressRef.current = false;

    const clearReconnectTimer = () => {
      if (reconnectTimerRef.current !== null) {
        clearTimeout(
          reconnectTimerRef.current,
        );

        reconnectTimerRef.current = null;
      }
    };

    const scheduleReconnect = () => {
      if (stoppedRef.current) {
        return;
      }

      if (
        reconnectTimerRef.current !== null
      ) {
        return;
      }

      reconnectTimerRef.current =
        setTimeout(() => {
          reconnectTimerRef.current = null;
          connect();
        }, 3000);
    };

    const connect = () => {
      if (stoppedRef.current) {
        return;
      }

      if (connectInProgressRef.current) {
        return;
      }

      const existing =
        websocketRef.current;

      if (
        existing &&
        (
          existing.readyState ===
            WebSocket.CONNECTING ||
          existing.readyState ===
            WebSocket.OPEN
        )
      ) {
        return;
      }

      connectInProgressRef.current = true;

      try {
        const url = getWebSocketUrl();

        console.log(
          'Connecting OFFGRID WebSocket:',
          url,
        );

        const socket = new WebSocket(url);

        websocketRef.current = socket;

        socket.onopen = () => {
          connectInProgressRef.current =
            false;

          console.log(
            'OFFGRID WebSocket connected',
          );
        };

        socket.onmessage = (event) => {
          try {
            const message =
              JSON.parse(event.data);

            if (
              message?.type ===
                'NETWORK_STATE' &&
              message?.data
            ) {
              applySnapshot(
                message.data,
              );
            }
          } catch (err) {
            console.error(
              'Invalid WebSocket message:',
              err,
            );
          }
        };

        socket.onerror = (event) => {
          connectInProgressRef.current =
            false;

          console.warn(
            'OFFGRID WebSocket unavailable:',
            event,
          );
        };

        socket.onclose = () => {
          connectInProgressRef.current =
            false;

          if (
            websocketRef.current ===
            socket
          ) {
            websocketRef.current = null;
          }

          console.warn(
            'OFFGRID WebSocket closed',
          );

          scheduleReconnect();
        };
      } catch (err) {
        connectInProgressRef.current =
          false;

        console.error(
          'OFFGRID WebSocket creation failed:',
          err,
        );

        websocketRef.current = null;

        scheduleReconnect();
      }
    };

    clearReconnectTimer();
    connect();

    return () => {
      stoppedRef.current = true;
      connectInProgressRef.current = false;

      clearReconnectTimer();

      const socket =
        websocketRef.current;

      websocketRef.current = null;

      if (socket) {
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;

        if (
          socket.readyState ===
            WebSocket.OPEN ||
          socket.readyState ===
            WebSocket.CONNECTING
        ) {
          socket.close();
        }
      }
    };
  }, [applySnapshot]);

  // ---------------------------------------------------------------------------
  // Toggle internet
  // ---------------------------------------------------------------------------

  const toggleInternet =
    useCallback(async () => {
      try {
        setError(null);

        const nextInternetState =
          !internetOnline;

        const response =
          (await apiToggleInternet(
            nextInternetState,
          )) as ApiActionResponse;

        applySnapshot({
          nodes: response.nodes,
          links: response.links,
          activeRoute:
            response.activeRoute ??
            response.route,
          metrics: response.metrics,
          logs: response.logs,
          internetOnline:
            response.internetOnline ??
            nextInternetState,
        });

        await refreshNetwork();
      } catch (err) {
        console.error(
          'Toggle internet failed:',
          err,
        );

        setError(
          err instanceof Error
            ? err.message
            : 'Failed to toggle internet',
        );

        await refreshNetwork();
      }
    }, [
      applySnapshot,
      internetOnline,
      refreshNetwork,
    ]);

  // ---------------------------------------------------------------------------
  // Kill node
  // ---------------------------------------------------------------------------

  const killNode = useCallback(
    async (
      nodeId: 'NODE_C' | 'NODE_E',
    ) => {
      try {
        setError(null);

        const response =
          (await apiKillNode(
            nodeId,
          )) as ApiActionResponse;

        applySnapshot({
          nodes: response.nodes,
          links: response.links,
          activeRoute:
            response.activeRoute ??
            response.route,
          metrics: response.metrics,
          logs: response.logs,
          internetOnline:
            response.internetOnline,
        });

        await refreshNetwork();
      } catch (err) {
        console.error(
          'Kill node failed:',
          err,
        );

        setError(
          err instanceof Error
            ? err.message
            : `Failed to kill ${nodeId}`,
        );

        await refreshNetwork();
      }
    },
    [applySnapshot, refreshNetwork],
  );

  // ---------------------------------------------------------------------------
  // Restore node
  // ---------------------------------------------------------------------------

  const restoreNode = useCallback(
    async (
      nodeId: 'NODE_C' | 'NODE_E',
    ) => {
      try {
        setError(null);

        const response =
          (await apiRestoreNode(
            nodeId,
          )) as ApiActionResponse;

        applySnapshot({
          nodes: response.nodes,
          links: response.links,
          activeRoute:
            response.activeRoute ??
            response.route,
          metrics: response.metrics,
          logs: response.logs,
          internetOnline:
            response.internetOnline,
        });

        await refreshNetwork();
      } catch (err) {
        console.error(
          'Restore node failed:',
          err,
        );

        setError(
          err instanceof Error
            ? err.message
            : `Failed to restore ${nodeId}`,
        );

        await refreshNetwork();
      }
    },
    [applySnapshot, refreshNetwork],
  );

  // ---------------------------------------------------------------------------
  // Send P2P message / file
  // ---------------------------------------------------------------------------

  const sendTransfer = useCallback(
    async (
      type: 'MESSAGE' | 'FILE',
    ) => {
      if (
        transferState.isTransferring
      ) {
        setTransferState(
          (current) => ({
            ...current,
            messageQueue:
              current.messageQueue + 1,
          }),
        );

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

        const response =
          (await sendMessage(
            'NODE_A',
            'NODE_E',
            'Emergency evacuation at Block B.',
          )) as ApiActionResponse;

        const route =
          response.route ??
          response.activeRoute ??
          response.metrics
            ?.activePathHops ??
          [];

        setActiveRoute(route);

        if (
          response.status ===
            'DELIVERED'
        ) {
          setTransferState({
            isTransferring: false,
            transferType: null,
            transferProgress: 100,
            messageQueue: 0,
          });

          await refreshNetwork();

          return;
        }

        if (
          response.status ===
            'PENDING'
        ) {
          setTransferState({
            isTransferring: false,
            transferType: null,
            transferProgress: 0,
            messageQueue: 1,
          });

          await refreshNetwork();

          setError(
            'Destination is offline. Message stored for forwarding.',
          );

          return;
        }

        setTransferState({
          isTransferring: false,
          transferType: null,
          transferProgress: 0,
          messageQueue: 0,
        });

        setError(
          response.message ??
            'Message was not delivered.',
        );

        await refreshNetwork();
      } catch (err) {
        console.error(
          'P2P message failed:',
          err,
        );

        setTransferState({
          isTransferring: false,
          transferType: null,
          transferProgress: 0,
          messageQueue: 0,
        });

        setError(
          err instanceof Error
            ? err.message
            : 'Failed to send P2P message',
        );

        await refreshNetwork();
      }
    },
    [
      refreshNetwork,
      transferState.isTransferring,
    ],
  );

  // ---------------------------------------------------------------------------
  // Reset network
  // ---------------------------------------------------------------------------

  const resetNetwork =
    useCallback(async () => {
      try {
        setError(null);

        const response =
          (await apiResetNetwork()) as ApiActionResponse;

        setTransferState(
          EMPTY_TRANSFER_STATE,
        );

        applySnapshot({
          nodes: response.nodes,
          links: response.links,
          activeRoute:
            response.activeRoute ??
            response.route,
          metrics: response.metrics,
          logs: response.logs,
          internetOnline:
            response.internetOnline,
        });

        await refreshNetwork();
      } catch (err) {
        console.error(
          'Reset network failed:',
          err,
        );

        setError(
          err instanceof Error
            ? err.message
            : 'Failed to reset network',
        );

        await refreshNetwork();
      }
    }, [applySnapshot, refreshNetwork]);

  // ---------------------------------------------------------------------------
  // Selected node
  // ---------------------------------------------------------------------------

  const selectedNode =
    nodes.find(
      (node) =>
        node.id === selectedNodeId,
    ) ??
    nodes[0] ??
    ({
      id: DEFAULT_SELECTED_NODE,
      label: 'Loading...',
      status: 'OFFLINE',
      ip: '0.0.0.0',
      latencyMs: 0,
      storedPacketsCount: 0,
      x: 50,
      y: 50,
      neighbors: [],
      lastSeenMs: 0,
    } satisfies MeshNode);

  // ---------------------------------------------------------------------------
  // Public hook API
  // ---------------------------------------------------------------------------

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