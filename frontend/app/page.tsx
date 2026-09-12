'use client';

import { useNetworkState } from '@/hooks/useNetworkState';
import { Header } from '@/components/layout/Header';
import { NetworkGraph } from '@/components/graph/NetworkGraph';
import { RouteDisplay } from '@/components/graph/RouteDisplay';
import { EventStream } from '@/components/telemetry/EventStream';
import { FailureSimulator } from '@/components/simulator/FailureSimulator';
import { Server, Radio, Database } from 'lucide-react';

export default function Home() {
  const { nodes, links, activeRoute, internetOnline, logs, metrics, actions } = useNetworkState();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans select-none">
      <Header internetOnline={internetOnline} onToggleInternet={actions.toggleInternet} />

      <main className="flex-1 p-6 grid grid-cols-12 gap-6 max-w-[1800px] w-full mx-auto">
        <div className="col-span-3 space-y-4">
          <div className="grid grid-cols-2 gap-3 font-mono">
            <div className="bg-slate-900 border border-slate-800 p-3 rounded-lg">
              <div className="text-slate-500 text-[10px] uppercase flex items-center space-x-1">
                <Server className="w-3 h-3 text-cyan-400" />
                <span>Nodes</span>
              </div>
              <div className="text-xl font-bold text-cyan-400 mt-1">
                {metrics.activeNodes} / {metrics.totalNodes}
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-3 rounded-lg">
              <div className="text-slate-500 text-[10px] uppercase flex items-center space-x-1">
                <Radio className="w-3 h-3 text-emerald-400" />
                <span>Latency</span>
              </div>
              <div className="text-xl font-bold text-emerald-400 mt-1">
                {metrics.avgMeshLatencyMs} ms
              </div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 font-mono">
            <h2 className="text-xs font-bold text-slate-400 uppercase mb-3 flex items-center justify-between">
              <span>Discovered Nodes</span>
              <Database className="w-3.5 h-3.5 text-slate-500" />
            </h2>
            <div className="space-y-2">
              {nodes.map(node => (
                <div
                  key={node.id}
                  className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800/80 text-xs"
                >
                  <div>
                    <div className="font-bold text-slate-200">{node.label}</div>
                    <div className="text-[10px] text-slate-500">{node.ip}</div>
                  </div>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                      node.status === 'OFFLINE'
                        ? 'bg-red-950 text-red-400 border border-red-800'
                        : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                    }`}
                  >
                    {node.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="col-span-6 space-y-4">
          <RouteDisplay activeRoute={activeRoute} />
          <NetworkGraph nodes={nodes} links={links} activeRoute={activeRoute} />
          <FailureSimulator
            onTriggerNodeC={actions.triggerNodeCFailure}
            onToggleInternet={actions.toggleInternet}
            onReset={actions.resetNetwork}
            internetOnline={internetOnline}
            isNodeCOffline={nodes.find(n => n.id === 'NODE_C')?.status === 'OFFLINE'}
          />
        </div>

        <div className="col-span-3">
          <EventStream logs={logs} />
        </div>
      </main>
    </div>
  );
}