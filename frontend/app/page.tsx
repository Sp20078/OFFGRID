'use client';

import { useState } from 'react';
import { useNetworkState } from '@/hooks/useNetworkState';
import { Header, NavTab } from '@/components/layout/Header';
import { NetworkGraph } from '@/components/graph/NetworkGraph';
import { NodeInspector } from '@/components/inspector/NodeInspector';
import { ActivityBar } from '@/components/activity/ActivityBar';
import { EventStream } from '@/components/telemetry/EventStream';
import { LiveStatus } from '@/components/live/LiveStatus';

export default function Home() {
  const [activeTab, setActiveTab] = useState<NavTab>('network');
  const {
    nodes,
    links,
    activeRoute,
    selectedNode,
    setSelectedNodeId,
    logs,
    metrics,
    liveMode,
    sendingMessage,
    sendMessageToNode,
    messageEvents
  } = useNetworkState();

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-mono select-none">
      {/* Top Header with Navigation Tabs */}
      <Header activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content Area */}
      <main className="flex-1 p-4 md:p-6 max-w-7xl w-full mx-auto">
        {/* VIEW 1: TOPOLOGY & SIMULATOR (Live Topology + Controls in Same Viewport) */}
        {activeTab === 'network' && (
          <div className="space-y-4">
            {/* Top Row: Mesh Graph + Dynamic Inspector */}
            <div className="grid grid-cols-12 gap-4 items-start">
              <div className="col-span-12 lg:col-span-8">
                <NetworkGraph
                  nodes={nodes}
                  links={links}
                  activeRoute={activeRoute}
                  metrics={metrics}
                  selectedNodeId={selectedNode.id}
                  onSelectNode={setSelectedNodeId}
                />
              </div>

              <div className="col-span-12 lg:col-span-4">
                <NodeInspector node={selectedNode} />
              </div>
            </div>

            {/* Live node activation + message tracker (real mode) */}
            <LiveStatus nodes={nodes} messageEvents={messageEvents} liveMode={liveMode} />
          </div>
        )}

        {/* VIEW 2: TRANSFERS (real P2P message composer) */}
        {activeTab === 'transfers' && (
          <ActivityBar
            nodes={nodes}
            liveMode={liveMode}
            sendingMessage={sendingMessage}
            onSendCustomMessage={sendMessageToNode}
          />
        )}

        {/* VIEW 3: AUDIT LOGS (Real-time Event Stream) */}
        {activeTab === 'logs' && <EventStream logs={logs} />}
      </main>
    </div>
  );
}