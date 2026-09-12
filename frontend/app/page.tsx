'use client';

import { useMemo, useState } from 'react';

import CustomMessageBox from '@/components/CustomMessageBox';
import { useNetworkState } from '@/hooks/useNetworkState';

export default function HomePage() {
  const {
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
    actions,
  } = useNetworkState();

  const [showEvents, setShowEvents] =
    useState(true);

  const [quickMessage, setQuickMessage] =
    useState('');

  const onlineNodes = useMemo(
    () =>
      nodes.filter(
        (node) =>
          node.status !== 'OFFLINE',
      ),
    [nodes],
  );

  const offlineNodes = useMemo(
    () =>
      nodes.filter(
        (node) =>
          node.status === 'OFFLINE',
      ),
    [nodes],
  );

  const activeRouteSet = useMemo(
    () => new Set(activeRoute),
    [activeRoute],
  );

  const routeText =
    activeRoute.length > 0
      ? activeRoute.join(' → ')
      : 'No active route';

  const isLinkOnRoute = (
    source: string,
    target: string,
  ) => {
    for (
      let index = 0;
      index < activeRoute.length - 1;
      index += 1
    ) {
      const first =
        activeRoute[index];

      const second =
        activeRoute[index + 1];

      if (
        (first === source &&
          second === target) ||
        (first === target &&
          second === source)
      ) {
        return true;
      }
    }

    return false;
  };

  const handleQuickMessage =
    async () => {
      const message =
        quickMessage.trim();

      if (!message) {
        return;
      }

      const destination =
        nodes.find(
          (node) =>
            node.id !== 'NODE_A' &&
            node.status !== 'OFFLINE',
        )?.id;

      if (!destination) {
        return;
      }

      const success =
        await actions.sendCustomMessage(
          message,
          destination,
          'NODE_A',
        );

      if (success) {
        setQuickMessage('');
      }
    };

  return (
    <main className="min-h-screen bg-[#070707] text-white">
      {/* ================================================================== */}
      {/* HEADER */}
      {/* ================================================================== */}

      <header className="sticky top-0 z-50 border-b border-white/10 bg-[#070707]/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/15 bg-white/5 text-sm font-bold">
              O
            </div>

            <div>
              <h1 className="text-lg font-semibold tracking-tight">
                OFFGRID
              </h1>

              <p className="text-[10px] uppercase tracking-[0.22em] text-white/35">
                Network That Survives the Internet
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-[10px] uppercase tracking-wider text-white/35">
                Internet
              </div>

              <div
                className={`text-xs font-medium ${
                  internetOnline
                    ? 'text-emerald-300'
                    : 'text-red-300'
                }`}
              >
                {internetOnline
                  ? 'ONLINE'
                  : 'OFFLINE'}
              </div>
            </div>

            <span
              className={`h-2.5 w-2.5 rounded-full ${
                internetOnline
                  ? 'bg-emerald-400'
                  : 'bg-red-400'
              }`}
            />
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1600px] px-6 py-6">
        {/* ================================================================= */}
        {/* ERROR */}
        {/* ================================================================= */}

        {error && (
          <div className="mb-6 rounded-2xl border border-red-400/20 bg-red-400/5 px-4 py-3">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-sm font-medium text-red-300">
                  Network status
                </div>

                <div className="mt-1 text-xs text-red-200/70">
                  {error}
                </div>
              </div>

              <button
                type="button"
                onClick={() =>
                  void actions.refreshNetwork()
                }
                className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-white/70 hover:bg-white/5"
              >
                Refresh
              </button>
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* METRICS */}
        {/* ================================================================= */}

        <section className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <MetricCard
            label="Total nodes"
            value={metrics.totalNodes}
          />

          <MetricCard
            label="Active nodes"
            value={metrics.activeNodes}
          />

          <MetricCard
            label="Active links"
            value={metrics.activeLinksCount}
          />

          <MetricCard
            label="Route hops"
            value={activeRoute.length}
          />

          <MetricCard
            label="Queue"
            value={
              metrics.storeAndForwardQueueSize
            }
          />

          <MetricCard
            label="Avg latency"
            value={`${Math.round(
              metrics.avgMeshLatencyMs,
            )} ms`}
          />
        </section>

        {/* ================================================================= */}
        {/* MAIN GRID */}
        {/* ================================================================= */}

        <div className="grid gap-6 xl:grid-cols-[1.7fr_1fr]">
          {/* =============================================================== */}
          {/* LEFT COLUMN */}
          {/* =============================================================== */}

          <div className="space-y-6">
            {/* ------------------------------------------------------------- */}
            {/* TOPOLOGY */}
            {/* ------------------------------------------------------------- */}

            <section className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02]">
              <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
                <div>
                  <h2 className="text-sm font-semibold">
                    Live mesh topology
                  </h2>

                  <p className="mt-1 text-xs text-white/35">
                    Real-time OFFGRID network state
                  </p>
                </div>

                <div className="flex items-center gap-4 text-[10px] text-white/40">
                  <span className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-400" />
                    Online
                  </span>

                  <span className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-red-400" />
                    Offline
                  </span>
                </div>
              </div>

              <div className="relative min-h-[430px] p-6">
                {loading && (
                  <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                    <div className="rounded-xl border border-white/10 bg-black/60 px-4 py-3 text-xs text-white/50">
                      Loading network...
                    </div>
                  </div>
                )}

                <div className="relative mx-auto h-[360px] max-w-[1000px]">
                  {/* Links */}

                  <svg
                    className="absolute inset-0 h-full w-full"
                    viewBox="0 0 1000 360"
                    preserveAspectRatio="none"
                  >
                    {links.map(
                      (link, index) => {
                        const sourceNode =
                          nodes.find(
                            (node) =>
                              node.id ===
                              link.source,
                          );

                        const targetNode =
                          nodes.find(
                            (node) =>
                              node.id ===
                              link.target,
                          );

                        if (
                          !sourceNode ||
                          !targetNode
                        ) {
                          return null;
                        }

                        const onRoute =
                          isLinkOnRoute(
                            link.source,
                            link.target,
                          );

                        const active =
                          link.active;

                        return (
                          <line
                            key={`${link.source}-${link.target}-${index}`}
                            x1={`${sourceNode.x}%`}
                            y1={`${sourceNode.y}%`}
                            x2={`${targetNode.x}%`}
                            y2={`${targetNode.y}%`}
                            stroke={
                              onRoute
                                ? 'rgba(255,255,255,0.95)'
                                : active
                                  ? 'rgba(255,255,255,0.25)'
                                  : 'rgba(255,255,255,0.08)'
                            }
                            strokeWidth={
                              onRoute
                                ? 3
                                : 1.5
                            }
                            strokeDasharray={
                              onRoute
                                ? undefined
                                : '6 6'
                            }
                          />
                        );
                      },
                    )}
                  </svg>

                  {/* Nodes */}

                  {nodes.map(
                    (node) => {
                      const online =
                        node.status !==
                        'OFFLINE';

                      const selected =
                        node.id ===
                        selectedNodeId;

                      const onRoute =
                        activeRouteSet.has(
                          node.id,
                        );

                      return (
                        <button
                          key={node.id}
                          type="button"
                          onClick={() =>
                            setSelectedNodeId(
                              node.id,
                            )
                          }
                          className="absolute -translate-x-1/2 -translate-y-1/2"
                          style={{
                            left: `${node.x}%`,
                            top: `${node.y}%`,
                          }}
                        >
                          <div
                            className={[
                              'flex min-w-[120px] flex-col items-center rounded-2xl border px-4 py-3 backdrop-blur-md transition',
                              selected
                                ? 'border-white/60 bg-white/10'
                                : 'border-white/10 bg-black/80',
                              onRoute
                                ? 'shadow-[0_0_30px_rgba(255,255,255,0.08)] ring-2 ring-white/15'
                                : '',
                            ].join(' ')}
                          >
                            <span
                              className={`mb-2 h-3 w-3 rounded-full ${
                                online
                                  ? 'bg-emerald-400'
                                  : 'bg-red-400'
                              }`}
                            />

                            <div className="text-xs font-semibold">
                              {node.label ??
                                node.id}
                            </div>

                            <div className="mt-1 text-[10px] text-white/35">
                              {node.id}
                            </div>

                            <div className="mt-2 text-[10px] text-white/35">
                              {online
                                ? `${Math.round(
                                    node.latencyMs,
                                  )} ms`
                                : 'OFFLINE'}
                            </div>
                          </div>
                        </button>
                      );
                    },
                  )}
                </div>
              </div>

              {/* Route */}

              <div className="border-t border-white/10 px-5 py-4">
                <div className="mb-2 text-[10px] uppercase tracking-wider text-white/35">
                  Active route
                </div>

                <div className="overflow-x-auto rounded-xl bg-black/30 px-4 py-3 font-mono text-xs text-white/75">
                  {routeText}
                </div>
              </div>
            </section>

            {/* ------------------------------------------------------------- */}
            {/* CUSTOM MESSAGE */}
            {/* ------------------------------------------------------------- */}

            <CustomMessageBox />

            {/* ------------------------------------------------------------- */}
            {/* QUICK SEND */}
            {/* ------------------------------------------------------------- */}

            <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <div className="mb-4">
                <h2 className="text-sm font-semibold">
                  Quick message
                </h2>

                <p className="mt-1 text-xs text-white/35">
                  Sends from NODE_A to the first available node.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <input
                  type="text"
                  value={quickMessage}
                  onChange={(event) =>
                    setQuickMessage(
                      event.target.value,
                    )
                  }
                  onKeyDown={(event) => {
                    if (
                      event.key ===
                        'Enter' &&
                      event.ctrlKey
                    ) {
                      event.preventDefault();

                      void handleQuickMessage();
                    }
                  }}
                  placeholder="Type a quick test message..."
                  className="min-w-0 flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-white/25 focus:border-white/30"
                />

                <button
                  type="button"
                  disabled={
                    !quickMessage.trim() ||
                    transferState.isTransferring
                  }
                  onClick={() =>
                    void handleQuickMessage()
                  }
                  className="rounded-xl bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {transferState.isTransferring
                    ? 'Sending...'
                    : 'Send'}
                </button>
              </div>
            </section>
          </div>

          {/* =============================================================== */}
          {/* RIGHT COLUMN */}
          {/* =============================================================== */}

          <aside className="space-y-6">
            {/* ------------------------------------------------------------- */}
            {/* SELECTED NODE */}
            {/* ------------------------------------------------------------- */}

            <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold">
                    Selected node
                  </h2>

                  <p className="mt-1 text-xs text-white/35">
                    Node inspection
                  </p>
                </div>

                <span
                  className={`h-2.5 w-2.5 rounded-full ${
                    selectedNode.status ===
                    'OFFLINE'
                      ? 'bg-red-400'
                      : 'bg-emerald-400'
                  }`}
                />
              </div>

              <div className="space-y-4">
                <InfoRow
                  label="Node ID"
                  value={
                    selectedNode.id
                  }
                />

                <InfoRow
                  label="Label"
                  value={
                    selectedNode.label
                  }
                />

                <InfoRow
                  label="Address"
                  value={
                    selectedNode.ip ||
                    '—'
                  }
                />

                <InfoRow
                  label="Status"
                  value={
                    selectedNode.status
                  }
                />

                <InfoRow
                  label="Latency"
                  value={`${Math.round(
                    selectedNode.latencyMs,
                  )} ms`}
                />

                <InfoRow
                  label="Stored packets"
                  value={
                    selectedNode.storedPacketsCount
                  }
                />

                <InfoRow
                  label="Neighbors"
                  value={
                    selectedNode.neighbors
                      .length > 0
                      ? selectedNode.neighbors.join(
                          ', ',
                        )
                      : 'None'
                  }
                />
              </div>
            </section>

            {/* ------------------------------------------------------------- */}
            {/* FAILURE CONTROLS */}
            {/* ------------------------------------------------------------- */}

            <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <div className="mb-4">
                <h2 className="text-sm font-semibold">
                  Failure simulation
                </h2>

                <p className="mt-1 text-xs text-white/35">
                  Test rerouting and store-and-forward.
                </p>
              </div>

              <div className="space-y-3">
                <ControlButton
                  danger
                  onClick={() =>
                    void actions.killNode(
                      'NODE_C',
                    )
                  }
                >
                  <strong>
                    Kill NODE_C
                  </strong>

                  <span>
                    Force alternate routing
                  </span>
                </ControlButton>

                <ControlButton
                  success
                  onClick={() =>
                    void actions.restoreNode(
                      'NODE_C',
                    )
                  }
                >
                  <strong>
                    Restore NODE_C
                  </strong>

                  <span>
                    Return node to mesh
                  </span>
                </ControlButton>

                <ControlButton
                  danger
                  onClick={() =>
                    void actions.killNode(
                      'NODE_E',
                    )
                  }
                >
                  <strong>
                    Kill NODE_E
                  </strong>

                  <span>
                    Test message storage
                  </span>
                </ControlButton>

                <ControlButton
                  success
                  onClick={() =>
                    void actions.restoreNode(
                      'NODE_E',
                    )
                  }
                >
                  <strong>
                    Restore NODE_E
                  </strong>

                  <span>
                    Attempt queued delivery
                  </span>
                </ControlButton>

                <ControlButton
                  onClick={() =>
                    void actions.toggleInternet()
                  }
                >
                  <strong>
                    {internetOnline
                      ? 'Disconnect internet'
                      : 'Reconnect internet'}
                  </strong>

                  <span>
                    Mesh remains local-first
                  </span>
                </ControlButton>

                <ControlButton
                  onClick={() =>
                    void actions.resetNetwork()
                  }
                >
                  <strong>
                    Reset network
                  </strong>

                  <span>
                    Restore healthy topology
                  </span>
                </ControlButton>
              </div>
            </section>

            {/* ------------------------------------------------------------- */}
            {/* NODE SUMMARY */}
            {/* ------------------------------------------------------------- */}

            <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <div className="mb-4">
                <h2 className="text-sm font-semibold">
                  Node summary
                </h2>
              </div>

              <div className="space-y-2">
                {nodes.map(
                  (node) => (
                    <button
                      key={node.id}
                      type="button"
                      onClick={() =>
                        setSelectedNodeId(
                          node.id,
                        )
                      }
                      className={`flex w-full items-center justify-between rounded-xl border px-3 py-3 text-left transition ${
                        node.id ===
                        selectedNodeId
                          ? 'border-white/25 bg-white/10'
                          : 'border-white/5 bg-white/[0.02] hover:bg-white/5'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className={`h-2.5 w-2.5 rounded-full ${
                            node.status ===
                            'OFFLINE'
                              ? 'bg-red-400'
                              : 'bg-emerald-400'
                          }`}
                        />

                        <div>
                          <div className="text-xs font-medium">
                            {node.id}
                          </div>

                          <div className="mt-0.5 text-[10px] text-white/30">
                            {node.status}
                          </div>
                        </div>
                      </div>

                      <div className="text-[10px] text-white/30">
                        {Math.round(
                          node.latencyMs,
                        )}{' '}
                        ms
                      </div>
                    </button>
                  ),
                )}
              </div>
            </section>
          </aside>
        </div>

        {/* ================================================================= */}
        {/* EVENT STREAM */}
        {/* ================================================================= */}

        <section className="mt-6 rounded-2xl border border-white/10 bg-white/[0.02]">
          <button
            type="button"
            onClick={() =>
              setShowEvents(
                (current) =>
                  !current,
              )
            }
            className="flex w-full items-center justify-between px-5 py-4 text-left"
          >
            <div>
              <h2 className="text-sm font-semibold">
                Event stream
              </h2>

              <p className="mt-1 text-xs text-white/35">
                Network activity and delivery events
              </p>
            </div>

            <span className="text-xs text-white/35">
              {showEvents
                ? 'Hide'
                : 'Show'}
            </span>
          </button>

          {showEvents && (
            <div className="border-t border-white/10">
              <div className="max-h-[320px] overflow-y-auto">
                {logs.length === 0 ? (
                  <div className="px-5 py-8 text-center text-xs text-white/30">
                    No events yet.
                  </div>
                ) : (
                  logs.map(
                    (log, index) => (
                      <div
                        key={`${String(
                          log.id,
                        )}-${String(
                          log.timestamp,
                        )}-${index}`}
                        className="flex gap-4 border-b border-white/5 px-5 py-3 last:border-b-0"
                      >
                        <div className="w-[75px] shrink-0 text-[10px] text-white/25">
                          {formatTimestamp(
                            log.timestamp,
                          )}
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-[10px] font-semibold uppercase ${
                                log.level ===
                                'ERROR'
                                  ? 'text-red-300'
                                  : log.level ===
                                      'WARN'
                                    ? 'text-yellow-300'
                                    : log.level ===
                                        'SUCCESS'
                                      ? 'text-emerald-300'
                                      : 'text-white/45'
                              }`}
                            >
                              {log.level}
                            </span>

                            {log.nodeId && (
                              <span className="text-[10px] text-white/25">
                                {log.nodeId}
                              </span>
                            )}
                          </div>

                          <div className="mt-1 break-words text-xs text-white/70">
                            {log.message}
                          </div>
                        </div>
                      </div>
                    ),
                  )
                )}
              </div>
            </div>
          )}
        </section>

        {/* ================================================================= */}
        {/* FOOTER */}
        {/* ================================================================= */}

        <footer className="flex flex-col gap-2 py-6 text-[10px] text-white/25 sm:flex-row sm:items-center sm:justify-between">
          <div>
            OFFGRID · Local-first decentralized mesh
          </div>

          <div className="flex gap-4">
            <span>
              Online {onlineNodes.length}
            </span>

            <span>
              Offline {offlineNodes.length}
            </span>

            <span>
              Queue{' '}
              {
                metrics.storeAndForwardQueueSize
              }
            </span>
          </div>
        </footer>
      </div>
    </main>
  );
}

// =============================================================================
// Small components
// =============================================================================

function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4">
      <div className="text-[10px] uppercase tracking-wider text-white/35">
        {label}
      </div>

      <div className="mt-2 text-xl font-semibold">
        {value}
      </div>
    </div>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-white/5 pb-3 last:border-0 last:pb-0">
      <span className="text-xs text-white/35">
        {label}
      </span>

      <span className="max-w-[65%] text-right text-xs text-white/75">
        {value}
      </span>
    </div>
  );
}

function ControlButton({
  children,
  onClick,
  danger = false,
  success = false,
}: {
  children: React.ReactNode;
  onClick: () => void;
  danger?: boolean;
  success?: boolean;
}) {
  const wrapperClass =
    danger
      ? 'border-red-400/20 bg-red-400/5 hover:bg-red-400/10'
      : success
        ? 'border-emerald-400/20 bg-emerald-400/5 hover:bg-emerald-400/10'
        : 'border-white/10 bg-white/5 hover:bg-white/10';

  const titleClass =
    danger
      ? 'text-red-300'
      : success
        ? 'text-emerald-300'
        : 'text-white';

  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-xl border px-4 py-3 text-left transition ${wrapperClass}`}
    >
      <div
        className={`text-sm font-medium ${titleClass}`}
      >
        {children}
      </div>
    </button>
  );
}

function formatTimestamp(
  timestamp: string,
) {
  try {
    return new Date(
      timestamp,
    ).toLocaleTimeString(
      undefined,
      {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      },
    );
  } catch {
    return timestamp;
  }
}