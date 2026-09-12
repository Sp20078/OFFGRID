'use client';

import React from 'react';
import { MeshNode, MeshLink } from '@/types/network';
import { Server, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface NetworkGraphProps {
  nodes: MeshNode[];
  links: MeshLink[];
  activeRoute: string[];
}

export const NetworkGraph: React.FC<NetworkGraphProps> = ({ nodes, links, activeRoute }) => {
  const nodeMap = new Map(nodes.map(n => [n.id, n]));

  return (
    <div className="relative w-full h-[440px] bg-slate-950/80 border border-slate-800 rounded-lg overflow-hidden flex flex-col justify-between p-4">
      <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] opacity-40 pointer-events-none" />

      <div className="relative z-10 flex justify-between items-center text-xs font-mono text-slate-400 border-b border-slate-900 pb-2">
        <span className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400" />
          <span>TOPOLOGY VISUALIZER</span>
        </span>
        <span>PEER LINK ACTIVE</span>
      </div>

      {/* Shared Coordinate Space for Links and Nodes */}
      <div className="relative flex-1 w-full my-2 min-h-0">
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
          <defs>
            <linearGradient id="activeLinkGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#06B6D4" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#38BDF8" stopOpacity="0.8" />
            </linearGradient>
          </defs>

          {links.map((link, idx) => {
            const source = nodeMap.get(link.source);
            const target = nodeMap.get(link.target);
            if (!source || !target) return null;

            const isDisabled = source.status === 'OFFLINE' || target.status === 'OFFLINE';

            return (
              <line
                key={`link-${idx}`}
                x1={`${source.x}%`}
                y1={`${source.y}%`}
                x2={`${target.x}%`}
                y2={`${target.y}%`}
                stroke={isDisabled ? '#334155' : link.active ? 'url(#activeLinkGrad)' : '#1E293B'}
                strokeWidth={link.active ? '3' : '1.5'}
                strokeDasharray={isDisabled ? '4,4' : link.active ? 'none' : '2,2'}
                className="transition-all duration-700"
              />
            );
          })}
        </svg>

        <div className="absolute inset-0 w-full h-full z-10 pointer-events-none">
          {nodes.map(node => {
            const isOffline = node.status === 'OFFLINE';
            const isInRoute = activeRoute.includes(node.id);

            return (
              <div
                key={node.id}
                style={{ left: `${node.x}%`, top: `${node.y}%` }}
                className={`pointer-events-auto absolute -translate-x-1/2 -translate-y-1/2 p-3 rounded-lg border transition-all duration-500 w-36 ${
                  isOffline
                    ? 'bg-red-950/80 border-red-500/60 text-red-300 shadow-lg shadow-red-950/50'
                    : isInRoute
                    ? 'bg-slate-900/90 border-cyan-500/80 text-cyan-300 shadow-md shadow-cyan-950/50'
                    : 'bg-slate-900/50 border-slate-800 text-slate-500'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <Server className={`w-4 h-4 ${isOffline ? 'text-red-400' : 'text-cyan-400'}`} />
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-950/60 border border-slate-800">
                    {node.ip}
                  </span>
                </div>
                <div className="font-mono text-xs font-bold truncate">{node.label}</div>
                <div className="mt-2 pt-1 border-t border-slate-800/60 flex items-center justify-between text-[10px] font-mono">
                  <span>STATUS:</span>
                  <span className={`font-semibold flex items-center ${isOffline ? 'text-red-400' : 'text-emerald-400'}`}>
                    {isOffline ? <AlertTriangle className="w-2.5 h-2.5 mr-1" /> : <CheckCircle2 className="w-2.5 h-2.5 mr-1" />}
                    {isOffline ? 'OFFLINE' : 'ONLINE'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="relative z-10 flex items-center justify-between text-[11px] font-mono text-slate-400 bg-slate-900/90 px-3 py-1.5 rounded border border-slate-800">
        <div className="flex items-center space-x-4">
          <span className="flex items-center space-x-1">
            <span className="w-2.5 h-0.5 bg-cyan-400 inline-block" />
            <span>Active Hop</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2.5 h-0.5 bg-slate-700 inline-block" />
            <span>Fallback Mesh Link</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
            <span>Node Failed</span>
          </span>
        </div>
      </div>
    </div>
  );
};