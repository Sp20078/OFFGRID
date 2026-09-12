'use client';

import React from 'react';
import { NetworkMetrics, MeshNode } from '@/types/network';
import { Server, Share2, Route, Activity, Database, ChevronRight } from 'lucide-react';

interface NetworkStatusCardProps {
  metrics: NetworkMetrics;
  nodes: MeshNode[];
  activeRoute: string[];
  selectedNodeId: string;
  onSelectNode: (nodeId: string) => void;
}

export const NetworkStatusCard: React.FC<NetworkStatusCardProps> = ({
  metrics,
  nodes,
  activeRoute,
  selectedNodeId,
  onSelectNode
}) => {
  return (
    <div className="w-full h-full bg-slate-950/80 border border-slate-800 rounded-lg p-4 flex flex-col justify-between font-mono select-none">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 text-xs text-slate-400">
          <span className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            <span className="font-bold text-slate-200 uppercase tracking-wider">NETWORK STATUS</span>
          </span>
          <span className="text-[10px] text-cyan-400/80 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-500/20">
            NOC V2.4
          </span>
        </div>

        {/* Primary Bullet Metric Items (Requested in wireframe) */}
        <div className="mt-4 space-y-3">
          <div className="flex items-center justify-between p-2.5 rounded bg-slate-900/90 border border-slate-800">
            <div className="flex items-center space-x-2 text-xs">
              <span className="text-cyan-400">•</span>
              <Server className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-slate-300 font-semibold">Nodes Online</span>
            </div>
            <span className="text-xs font-bold text-cyan-300 px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-500/30">
              {metrics.activeNodes} / {metrics.totalNodes}
            </span>
          </div>

          <div className="flex items-center justify-between p-2.5 rounded bg-slate-900/90 border border-slate-800">
            <div className="flex items-center space-x-2 text-xs">
              <span className="text-emerald-400">•</span>
              <Share2 className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-slate-300 font-semibold">Active Links</span>
            </div>
            <span className="text-xs font-bold text-emerald-300 px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-500/30">
              {metrics.activeLinksCount} Links
            </span>
          </div>

          <div className="p-2.5 rounded bg-slate-900/90 border border-slate-800">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <div className="flex items-center space-x-2">
                <span className="text-amber-400">•</span>
                <Route className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-slate-300 font-semibold">1 Computed Route</span>
              </div>
              <span className="text-[10px] text-amber-400/80">OPTIMAL</span>
            </div>
            <div className="flex flex-wrap items-center gap-1 text-[11px] pt-1">
              {activeRoute.map((nodeId, idx) => (
                <React.Fragment key={nodeId}>
                  <span className="px-1.5 py-0.5 bg-slate-950 border border-cyan-500/30 text-cyan-300 rounded font-bold">
                    {nodeId.replace('NODE_', '')}
                  </span>
                  {idx < activeRoute.length - 1 && (
                    <ChevronRight className="w-3 h-3 text-slate-600" />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>

        {/* Secondary Telemetry: Latency & Store-and-Forward Buffer */}
        <div className="grid grid-cols-2 gap-2 mt-3 text-[11px]">
          <div className="p-2 rounded bg-slate-900/50 border border-slate-800/80">
            <div className="text-slate-500 text-[10px] flex items-center space-x-1">
              <Activity className="w-3 h-3 text-cyan-400" />
              <span>MESH LATENCY</span>
            </div>
            <div className="text-sm font-bold text-slate-200 mt-1">
              {metrics.avgMeshLatencyMs} ms
            </div>
          </div>

          <div className="p-2 rounded bg-slate-900/50 border border-slate-800/80">
            <div className="text-slate-500 text-[10px] flex items-center space-x-1">
              <Database className="w-3 h-3 text-amber-400" />
              <span>S&F QUEUE</span>
            </div>
            <div className={`text-sm font-bold mt-1 ${metrics.storeAndForwardQueueSize > 0 ? 'text-amber-400 animate-pulse' : 'text-slate-300'}`}>
              {metrics.storeAndForwardQueueSize} pkts
            </div>
          </div>
        </div>
      </div>

      {/* Discovered Peer Nodes Quick Selector */}
      <div className="mt-4 pt-3 border-t border-slate-900">
        <div className="text-[10px] uppercase text-slate-500 mb-2 tracking-wider flex items-center justify-between">
          <span>SELECT TO INSPECT</span>
          <span className="text-[9px] text-slate-600">CLICK NODE</span>
        </div>
        <div className="grid grid-cols-5 gap-1">
          {nodes.map(node => {
            const isSelected = node.id === selectedNodeId;
            const isOffline = node.status === 'OFFLINE';

            return (
              <button
                key={node.id}
                onClick={() => onSelectNode(node.id)}
                className={`py-1.5 rounded text-[11px] font-bold border transition-all cursor-pointer ${
                  isSelected
                    ? 'border-cyan-400 bg-cyan-950/80 text-cyan-200 shadow-[0_0_8px_rgba(6,182,212,0.4)]'
                    : isOffline
                    ? 'border-red-900/60 bg-red-950/40 text-red-400 hover:border-red-600'
                    : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                }`}
              >
                {node.id.replace('NODE_', '')}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
