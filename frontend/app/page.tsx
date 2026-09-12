'use client';

import { useState } from 'react';
import { useNetworkState } from '@/hooks/useNetworkState';
import { Header, NavTab } from '@/components/layout/Header';
import { NetworkGraph } from '@/components/graph/NetworkGraph';
import { NodeInspector } from '@/components/inspector/NodeInspector';
import { SimulatorDeck } from '@/components/simulator/SimulatorDeck';
import { ActivityBar } from '@/components/activity/ActivityBar';
import { EventStream } from '@/components/telemetry/EventStream';

export default function Home() {
  const [activeTab, setActiveTab] = useState<NavTab>('network');
  const {
    nodes,
    links,
    activeRoute,
    selectedNode,
    setSelectedNodeId,
    internetOnline,
    logs,
    metrics,
    transferState,
    actions
  } = useNetworkState();

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-mono select-none">
      {/* Top Header with Navigation Tabs */}
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        internetOnline={internetOnline}
        onToggleInternet={actions.toggleInternet}
      />

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

            {/* Bottom Row: Chaos Simulator Controls (Directly updates topology above) */}
            <SimulatorDeck
              nodes={nodes}
              activeRoute={activeRoute}
              internetOnline={internetOnline}
              onToggleInternet={actions.toggleInternet}
              onKillNode={actions.killNode}
              onRestoreNode={actions.restoreNode}
              onResetNetwork={actions.resetNetwork}
            />
          </div>
        )}

        {/* VIEW 2: TRANSFERS (P2P Message & File Chunk Injection) */}
        {activeTab === 'transfers' && (
          <ActivityBar
            onSendMessage={() => actions.sendTransfer('MESSAGE')}
            onSendFile={() => actions.sendTransfer('FILE')}
            transferState={transferState}
            nodes={nodes}
          />
        )}

        {/* VIEW 3: AUDIT LOGS (Real-time Event Stream) */}
        {activeTab === 'logs' && <EventStream logs={logs} />}
      </main>
    </div>
  );
}