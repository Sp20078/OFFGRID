'use client';

import React from 'react';
import { MeshNode } from '@/types/network';

interface NodeInspectorProps {
  node: MeshNode;
}

export const NodeInspector: React.FC<NodeInspectorProps> = ({ node }) => {
  const isOffline = node.status === 'OFFLINE';

  return (
    <div className="w-full h-[400px] bg-zinc-900/40 border border-zinc-800 rounded-lg p-4 flex flex-col justify-between font-mono select-none">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-zinc-800 text-xs text-zinc-400">
          <span className="font-semibold text-zinc-100">Node Inspector</span>
          <span className="text-[11px] text-zinc-500">{node.id}</span>
        </div>

        {/* Selected Node Summary */}
        <div className="mt-4 p-3 rounded bg-zinc-900/90 border border-zinc-800">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-sm text-zinc-100">{node.label}</span>
            <div className="flex items-center space-x-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  isOffline ? 'bg-rose-500' : 'bg-emerald-400'
                }`}
              />
              <span className={`text-xs font-medium ${isOffline ? 'text-rose-400' : 'text-emerald-400'}`}>
                {node.status}
              </span>
            </div>
          </div>
          <div className="text-xs text-zinc-400 mt-1">IP: {node.ip}</div>
        </div>

        {/* Technical Attributes List */}
        <div className="mt-4 space-y-3 text-xs">
          <div className="flex items-center justify-between py-1.5 border-b border-zinc-800/60 text-zinc-400">
            <span>Roundtrip Latency</span>
            <span className="text-zinc-100 font-medium">{isOffline ? 'Unreachable' : `${node.latencyMs} ms`}</span>
          </div>

          <div className="flex items-center justify-between py-1.5 border-b border-zinc-800/60 text-zinc-400">
            <span>Last Heartbeat</span>
            <span className="text-zinc-100 font-medium">{isOffline ? 'Timed Out' : `${node.lastSeenMs}ms ago`}</span>
          </div>

          <div className="flex items-center justify-between py-1.5 border-b border-zinc-800/60 text-zinc-400">
            <span>Store & Forward Queue</span>
            <span className={`font-medium ${node.storedPacketsCount > 0 ? 'text-amber-400' : 'text-zinc-100'}`}>
              {node.storedPacketsCount} packets
            </span>
          </div>

          <div className="py-1.5 text-zinc-400">
            <div className="mb-1.5">Connected Neighbors</div>
            <div className="flex flex-wrap gap-1.5">
              {node.neighbors.map(neighbor => (
                <span
                  key={neighbor}
                  className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 text-[11px]"
                >
                  {neighbor}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Footer Role */}
      <div className="pt-3 border-t border-zinc-800/80 text-[11px] text-zinc-500 flex items-center justify-between">
        <span>Type: {node.id === 'NODE_A' ? 'Ingress Gateway' : node.id === 'NODE_E' ? 'Egress Target' : 'Mesh Router'}</span>
        <span>Mesh Node v1</span>
      </div>
    </div>
  );
};
