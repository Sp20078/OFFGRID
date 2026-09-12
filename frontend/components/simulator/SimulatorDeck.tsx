'use client';

import React from 'react';
import { MeshNode } from '@/types/network';

interface SimulatorDeckProps {
  nodes: MeshNode[];
  activeRoute: string[];
  internetOnline: boolean;
  onToggleInternet: () => void;
  onKillNode: (nodeId: 'NODE_C' | 'NODE_E') => void;
  onRestoreNode: (nodeId: 'NODE_C' | 'NODE_E') => void;
  onResetNetwork: () => void;
}

export const SimulatorDeck: React.FC<SimulatorDeckProps> = ({
  nodes,
  activeRoute,
  internetOnline,
  onToggleInternet,
  onKillNode,
  onRestoreNode,
  onResetNetwork
}) => {
  const isNodeCOffline = nodes.find(n => n.id === 'NODE_C')?.status === 'OFFLINE';
  const isNodeEOffline = nodes.find(n => n.id === 'NODE_E')?.status === 'OFFLINE';
  const nodeD = nodes.find(n => n.id === 'NODE_D');

  return (
    <div className="w-full bg-zinc-900/40 border border-zinc-800 rounded-lg p-4 font-mono select-none">
      {/* Simulator Header & Route Indicator */}
      <div className="flex flex-wrap items-center justify-between pb-3 border-b border-zinc-800/80 gap-3 text-xs">
        <div className="flex items-center space-x-3">
          <span className="font-semibold text-zinc-100">Chaos Simulator</span>
          <span className="text-zinc-600">|</span>
          <span className="text-zinc-400">
            Route:{' '}
            <span className="text-zinc-200 font-bold">
              {activeRoute.map(id => id.replace('NODE_', '')).join(' → ')}
            </span>
          </span>
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
              isNodeCOffline
                ? 'bg-amber-950/40 text-amber-400 border border-amber-800/50'
                : 'bg-emerald-950/40 text-emerald-400 border border-emerald-800/50'
            }`}
          >
            {isNodeCOffline ? 'FALLBACK PATH' : 'OPTIMAL PATH'}
          </span>
        </div>

        <div className="flex items-center space-x-3">
          {isNodeEOffline && (
            <span className="text-[11px] text-amber-400">
              ⚠️ Target Node E offline — Node D buffering ({nodeD?.storedPacketsCount || 0} pkts)
            </span>
          )}
          <button
            onClick={onResetNetwork}
            className="px-2.5 py-1 rounded text-xs border border-zinc-700 bg-zinc-800 text-zinc-300 hover:bg-zinc-700 hover:text-white transition-all cursor-pointer"
          >
            Reset All
          </button>
        </div>
      </div>

      {/* Control Action Buttons */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5 mt-3 text-xs">
        {/* WAN Control */}
        <button
          onClick={onToggleInternet}
          className={`py-2 px-3 rounded font-medium border transition-all cursor-pointer ${
            !internetOnline
              ? 'bg-amber-950/30 border-amber-600/80 text-amber-300 hover:bg-amber-900/40'
              : 'bg-zinc-900 border-zinc-700 text-zinc-200 hover:bg-zinc-800'
          }`}
        >
          {internetOnline ? 'Disconnect WAN' : 'Reconnect WAN'}
        </button>

        {/* Kill Node C */}
        <button
          onClick={() => onKillNode('NODE_C')}
          disabled={isNodeCOffline}
          className={`py-2 px-3 rounded font-medium border transition-all ${
            isNodeCOffline
              ? 'bg-zinc-950 border-zinc-800/80 text-zinc-600 cursor-not-allowed opacity-50'
              : 'bg-rose-950/30 border-rose-700/80 text-rose-300 hover:bg-rose-900/40 cursor-pointer'
          }`}
        >
          Kill Node C
        </button>

        {/* Restore Node C */}
        <button
          onClick={() => onRestoreNode('NODE_C')}
          disabled={!isNodeCOffline}
          className={`py-2 px-3 rounded font-medium border transition-all ${
            !isNodeCOffline
              ? 'bg-zinc-950 border-zinc-800/80 text-zinc-600 cursor-not-allowed opacity-50'
              : 'bg-emerald-950/30 border-emerald-700/80 text-emerald-300 hover:bg-emerald-900/40 cursor-pointer'
          }`}
        >
          Restore Node C
        </button>

        {/* Kill Node E */}
        <button
          onClick={() => onKillNode('NODE_E')}
          disabled={isNodeEOffline}
          className={`py-2 px-3 rounded font-medium border transition-all ${
            isNodeEOffline
              ? 'bg-zinc-950 border-zinc-800/80 text-zinc-600 cursor-not-allowed opacity-50'
              : 'bg-rose-950/30 border-rose-700/80 text-rose-300 hover:bg-rose-900/40 cursor-pointer'
          }`}
        >
          Kill Node E
        </button>

        {/* Restore Node E */}
        <button
          onClick={() => onRestoreNode('NODE_E')}
          disabled={!isNodeEOffline}
          className={`py-2 px-3 rounded font-medium border transition-all ${
            !isNodeEOffline
              ? 'bg-zinc-950 border-zinc-800/80 text-zinc-600 cursor-not-allowed opacity-50'
              : 'bg-emerald-950/30 border-emerald-700/80 text-emerald-300 hover:bg-emerald-900/40 cursor-pointer'
          }`}
        >
          Restore Node E
        </button>
      </div>
    </div>
  );
};
