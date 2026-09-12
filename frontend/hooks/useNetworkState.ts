'use client';

import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';

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

type ApiResponse = NetworkSnapshot & {
  status?: string;
  route?: string[];
  message?: string;
  message_id?: string;
};

const EMPTY_METRICS: NetworkMetrics = {
  totalNodes: 0,
  activeNodes: 0,
  activeLinksCount: 0,
  activePathHops: [],
  internetAvailable: false,
  storeAndForwardQueueSize: 0,
  avgMeshLatencyMs: 0,
};

const EMPTY_TRANSFER: TransferState = {
  isTransferring: false,
  transferType: null,
  transferProgress: 0,
  messageQueue: 0,
};

export function useNetworkState() {
  const [nodes, setNodes] =
    useState<MeshNode[]>([]);

  const [links, setLinks] =
    useState<MeshLink[]>([]);

  const [activeRoute, setActiveRoute] =
    useState<string[]>([]);

  const [selectedNodeId, setSelectedNodeId] =
    useState('NODE_A');

  const [internetOnline, setInternetOnline] =
    useState(false);

  const [logs, setLogs] =
    useState<NetworkLog[]>([]);

  const [metrics, setMetrics] =
    useState<NetworkMetrics>(
      EMPTY_METRICS,
    );

  const [transferState, setTransferState] =
    useState<TransferState>(
      EMPTY_TRANSFER,
    );

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const websocketRef =
    useRef<WebSocket | null>(null);

  const reconnectTimerRef =
    useRef<ReturnType<typeof setTimeout> | null>(
      null,
    );

  const stoppedRef =
    useRef(false);

  const connectingRef =
    useRef(false);

  // ---------------------------------------------------------------------------
  // Apply backend snapshot
  // ---------------------------------------------------------------------------

  const applySnapshot = useCallback(
    (snapshot: NetworkSnapshot) => {
      const nextNodes =
        snapshot.nodes ?? [];

      const nextLinks =
        snapshot.links ?? [];

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
            (node) =>
              node.status !== 'OFFLINE',
          ).length,
        activeLinksCount:
          snapshot.metrics
            ?.activeLinksCount ??
          nextLinks.filter(
            (link) => link.active,
          ).length,
        activePathHops:
          nextRoute,
        internetAvailable:
          snapshot.metrics
            ?.internetAvailable ??
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

      setSelectedNodeId(
        (current) => {
          if (
            nextNodes.some(
              (node) =>
                node.id === current,
            )
          ) {
            return current;
          }

          return (
            nextNodes[0]?.id ??
            'NODE_A'
          );
        },
      );
    },
    [],
  );

  // ---------------------------------------------------------------------------
  // Refresh state
  // ---------------------------------------------------------------------------

  const refreshNetwork =
    useCallback(async () => {
      try {
        const [
          nodesResponse,
          topologyResponse,
          metricsResponse,
          eventsResponse,
          routeResponse,
        ] = await Promise.all([
          getNodes(),
          getTopology(),
          getMetrics(),
          getEvents(),
          getRoute('NODE_E'),
        ]);

        const route =
          routeResponse?.route ??
          topologyResponse?.activeRoute ??
          metricsResponse?.activePathHops ??
          [];

        applySnapshot({
          nodes:
            nodesResponse ?? [],
          links:
            topologyResponse?.links ??
            [],
          activeRoute: route,
          metrics: {
            ...EMPTY_METRICS,
            ...(metricsResponse ?? {}),
            activePathHops: route,
          },
          logs:
            eventsResponse ?? [],
          internetOnline:
            metricsResponse?.internetAvailable ??
            false,
        });

        setError(null);
      } catch (err) {
        console.error(
          'OFFGRID refresh failed:',
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
    connectingRef.current = false;

    const clearReconnectTimer =
      () => {
        if (
          reconnectTimerRef.current !==
          null
        ) {
          clearTimeout(
            reconnectTimerRef.current,
          );

          reconnectTimerRef.current =
            null;
        }
      };

    const connect = () => {
      if (stoppedRef.current) {
        return;
      }

      if (connectingRef.current) {
        return;
      }

      const existing =
        websocketRef.current;

      if (
        existing &&
        (
          existing.readyState ===
            WebSocket.OPEN ||
          existing.readyState ===
            WebSocket.CONNECTING
        )
      ) {
        return;
      }

      connectingRef.current =
        true;

      try {
        const url =
          getWebSocketUrl();

        console.log(
          'Connecting OFFGRID WebSocket:',
          url,
        );

        const socket =
          new WebSocket(url);

        websocketRef.current =
          socket;

        socket.onopen = () => {
          connectingRef.current =
            false;

          console.log(
            'OFFGRID WebSocket connected',
          );
        };

        socket.onmessage = (
          event,
        ) => {
          try {
            const message =
              JSON.parse(
                event.data,
              );

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

        socket.onerror = () => {
          connectingRef.current =
            false;

          console.warn(
            'OFFGRID WebSocket temporarily unavailable.',
          );
        };

        socket.onclose = () => {
          connectingRef.current =
            false;

          if (
            websocketRef.current ===
            socket
          ) {
            websocketRef.current =
              null;
          }

          if (
            !stoppedRef.current
          ) {
            clearReconnectTimer();

            reconnectTimerRef.current =
              setTimeout(() => {
                reconnectTimerRef.current =
                  null;

                connect();
              }, 3000);
          }
        };
      } catch (err) {
        connectingRef.current =
          false;

        websocketRef.current =
          null;

        console.error(
          'WebSocket creation failed:',
          err,
        );

        if (
          !stoppedRef.current
        ) {
          clearReconnectTimer();

          reconnectTimerRef.current =
            setTimeout(() => {
              reconnectTimerRef.current =
                null;

              connect();
            }, 3000);
        }
      }
    };

    clearReconnectTimer();
    connect();

    return () => {
      stoppedRef.current = true;
      connectingRef.current =
        false;

      clearReconnectTimer();

      const socket =
        websocketRef.current;

      websocketRef.current =
        null;

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

        await apiToggleInternet(
          !internetOnline,
        );

        await refreshNetwork();
      } catch (err) {
        console.error(err);

        setError(
          err instanceof Error
            ? err.message
            : 'Failed to toggle internet',
        );

        await refreshNetwork();
      }
    }, [
      internetOnline,
      refreshNetwork,
    ]);

  // ---------------------------------------------------------------------------
  // Kill node
  // ---------------------------------------------------------------------------

  const killNode = useCallback(
    async (
      nodeId:
        | 'NODE_C'
        | 'NODE_E',
    ) => {
      try {
        setError(null);

        await apiKillNode(nodeId);

        await refreshNetwork();
      } catch (err) {
        console.error(err);

        setError(
          err instanceof Error
            ? err.message
            : `Failed to kill ${nodeId}`,
        );

        await refreshNetwork();
      }
    },
    [refreshNetwork],
  );

  // ---------------------------------------------------------------------------
  // Restore node
  // ---------------------------------------------------------------------------

  const restoreNode = useCallback(
    async (
      nodeId:
        | 'NODE_C'
        | 'NODE_E',
    ) => {
      try {
        setError(null);

        await apiRestoreNode(
          nodeId,
        );

        await refreshNetwork();
      } catch (err) {
        console.error(err);

        setError(
          err instanceof Error
            ? err.message
            : `Failed to restore ${nodeId}`,
        );

        await refreshNetwork();
      }
    },
    [refreshNetwork],
  );

  // ---------------------------------------------------------------------------
  // CUSTOM MESSAGE
  // ---------------------------------------------------------------------------

  const sendCustomMessage =
    useCallback(
      async (
        message: string,
        destination: string,
        source = 'NODE_A',
      ): Promise<boolean> => {
        const cleanMessage =
          message.trim();

        if (!cleanMessage) {
          setError(
            'Please enter a message.',
          );

          return false;
        }

        if (!destination) {
          setError(
            'Please select a destination.',
          );

          return false;
        }

        if (source === destination) {
          setError(
            'Source and destination must be different.',
          );

          return false;
        }

        try {
          setError(null);

          setTransferState({
            isTransferring: true,
            transferType: 'MESSAGE',
            transferProgress: 10,
            messageQueue: 0,
          });

          console.log(
            'Sending OFFGRID message:',
            {
              source,
              destination,
              payload: cleanMessage,
            },
          );

          const response =
            (await sendMessage(
              source,
              destination,
              cleanMessage,
            )) as ApiResponse;

          console.log(
            'OFFGRID message response:',
            response,
          );

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
              isTransferring:
                false,
              transferType: null,
              transferProgress: 100,
              messageQueue: 0,
            });

            await refreshNetwork();

            return true;
          }

          if (
            response.status ===
            'PENDING'
          ) {
            setTransferState({
              isTransferring:
                false,
              transferType: null,
              transferProgress: 0,
              messageQueue: 1,
            });

            await refreshNetwork();

            setError(
              `${destination} is offline. Message stored for forwarding.`,
            );

            return true;
          }

          setTransferState({
            isTransferring:
              false,
            transferType: null,
            transferProgress: 0,
            messageQueue: 0,
          });

          setError(
            response.message ??
              'Message was not delivered.',
          );

          await refreshNetwork();

          return false;
        } catch (err) {
          console.error(
            'Custom message failed:',
            err,
          );

          setTransferState({
            isTransferring:
              false,
            transferType: null,
            transferProgress: 0,
            messageQueue: 0,
          });

          setError(
            err instanceof Error
              ? err.message
              : 'Failed to send message',
          );

          await refreshNetwork();

          return false;
        }
      },
      [refreshNetwork],
    );

  // ---------------------------------------------------------------------------
  // Existing transfer compatibility
  // ---------------------------------------------------------------------------

  const sendTransfer =
    useCallback(
      async (
        type: 'MESSAGE' | 'FILE',
        customMessage?: string,
        destination = 'NODE_E',
      ) => {
        if (type === 'FILE') {
          setError(
            'File transfer backend integration is not connected yet.',
          );

          return false;
        }

        return sendCustomMessage(
          customMessage ??
            'Emergency evacuation at Block B.',
          destination,
          'NODE_A',
        );
      },
      [sendCustomMessage],
    );

  // ---------------------------------------------------------------------------
  // Reset
  // ---------------------------------------------------------------------------

  const resetNetwork =
    useCallback(async () => {
      try {
        setError(null);

        await apiResetNetwork();

        setTransferState(
          EMPTY_TRANSFER,
        );

        await refreshNetwork();
      } catch (err) {
        console.error(err);

        setError(
          err instanceof Error
            ? err.message
            : 'Failed to reset network',
        );

        await refreshNetwork();
      }
    }, [refreshNetwork]);

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
      id: 'NODE_A',
      label: 'Node A',
      status: 'OFFLINE',
      ip: '0.0.0.0',
      latencyMs: 0,
      storedPacketsCount: 0,
      x: 10,
      y: 50,
      neighbors: [],
      lastSeenMs: 0,
    } satisfies MeshNode);

  // ---------------------------------------------------------------------------
  // IMPORTANT: this is what page.tsx receives.
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
      sendCustomMessage,
      sendTransfer,
      resetNetwork,
      refreshNetwork,
    },
  };
}