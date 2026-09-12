'use client';

import React, { useMemo } from 'react';
import { MeshNode, MeshLink, NetworkMetrics } from '@/types/network';

interface NetworkGraphProps {
  nodes: MeshNode[];
  links: MeshLink[];
  activeRoute: string[];
  metrics: NetworkMetrics;
  selectedNodeId: string;
  onSelectNode: (nodeId: string) => void;
}

export const NetworkGraph: React.FC<NetworkGraphProps> = ({
  nodes,
  links,
  activeRoute,
  metrics,
  selectedNodeId,
  onSelectNode
}) => {
  const nodeMap = useMemo(() => new Map(nodes.map(n => [n.id, n])), [nodes]);

  // Compute SVG path string for the active route
  const activeRoutePath = useMemo(() => {
    if (activeRoute.length < 2) return '';
    const points = activeRoute
      .map(id => nodeMap.get(id))
      .filter((n): n is MeshNode => !!n);

    if (points.length < 2) return '';
    return points.reduce((acc, pt, idx) => {
      return idx === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`;
    }, '');
  }, [activeRoute, nodeMap]);

  return (
    <div className="relative w-full h-[400px] bg-zinc-900/40 border border-zinc-800 rounded-lg overflow-hidden flex flex-col justify-between p-4 font-mono select-none">
      {/* Top Telemetry Summary Bar (Replaces redundant separate status box) */}
      <div className="relative z-10 flex flex-wrap items-center justify-between text-xs pb-3 border-b border-zinc-800/80 gap-3">
        <div className="flex items-center space-x-4 text-zinc-300">
          <span className="font-semibold text-zinc-100">Topology Map</span>
          <span className="text-zinc-600">|</span>
          <span className="text-zinc-400">
            Nodes: <span className="text-zinc-100 font-bold">{metrics.activeNodes}/{metrics.totalNodes}</span>
          </span>
          <span className="text-zinc-400">
            Active Links: <span className="text-zinc-100 font-bold">{metrics.activeLinksCount}</span>
          </span>
          <span className="text-zinc-400">
            Latency: <span className="text-zinc-100 font-bold">{metrics.avgMeshLatencyMs}ms</span>
          </span>
        </div>

        {/* Current Path */}
        <div className="flex items-center space-x-1.5 text-xs">
          <span className="text-zinc-500">Route:</span>
          <div className="flex items-center space-x-1">
            {activeRoute.map((id, idx) => (
              <React.Fragment key={id}>
                <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-200 text-[11px] font-medium">
                  {id.replace('NODE_', '')}
                </span>
                {idx < activeRoute.length - 1 && <span className="text-zinc-600">→</span>}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>

      {/* Shared Coordinate Space for Links, Nodes, and Packet Movement */}
      <div className="relative flex-1 w-full my-3 min-h-0">
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none z-0"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
        >
          {/* Base Links */}
          {links.map((link, idx) => {
            const source = nodeMap.get(link.source);
            const target = nodeMap.get(link.target);
            if (!source || !target) return null;

            const isSevered = source.status === 'OFFLINE' || target.status === 'OFFLINE';

            return (
              <line
                key={`link-${idx}`}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke={isSevered ? '#f43f5e' : link.active ? '#a1a1aa' : '#3f3f46'}
                strokeWidth={link.active ? '0.8' : '0.5'}
                strokeDasharray={isSevered ? '1.5,1.5' : link.active ? 'none' : '1.5,1.5'}
                className="transition-all duration-300"
              />
            );
          })}

          {/* Clean Packet Motion along active path */}
          {activeRoutePath && (
            <circle r="1.4" fill="#e4e4e7">
              <animateMotion dur="2.8s" repeatCount="indefinite" path={activeRoutePath} />
            </circle>
          )}
        </svg>

        {/* Node Elements */}
        <div className="absolute inset-0 w-full h-full z-10 pointer-events-none">
          {nodes.map(node => {
            const isOffline = node.status === 'OFFLINE';
            const isSelected = node.id === selectedNodeId;

            return (
              <div
                key={node.id}
                onClick={() => onSelectNode(node.id)}
                style={{ left: `${node.x}%`, top: `${node.y}%` }}
                className={`pointer-events-auto absolute -translate-x-1/2 -translate-y-1/2 p-2.5 rounded border transition-all duration-200 w-32 cursor-pointer ${
                  isSelected
                    ? 'bg-zinc-900 border-zinc-200 ring-1 ring-zinc-400 text-zinc-100 z-20 shadow-md'
                    : isOffline
                    ? 'bg-zinc-950 border-rose-800 text-zinc-400 opacity-90'
                    : 'bg-zinc-900/90 border-zinc-800 text-zinc-300 hover:border-zinc-600 hover:text-zinc-100'
                }`}
              >
                {/* Node Top: Label + Status Dot */}
                <div className="flex items-center justify-between mb-1">
                  <div className="font-semibold text-xs truncate">{node.label}</div>
                  <span
                    className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                      isOffline ? 'bg-rose-500' : 'bg-emerald-400'
                    }`}
                  />
                </div>

                {/* Node Metadata */}
                <div className="flex items-center justify-between text-[10px] text-zinc-400 pt-1 border-t border-zinc-800/60">
                  <span>{node.ip}</span>
                  <span className={isOffline ? 'text-rose-400' : 'text-zinc-400'}>
                    {isOffline ? 'DOWN' : `${node.latencyMs}ms`}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Clean Bottom Legend */}
      <div className="relative z-10 flex items-center justify-between text-[11px] text-zinc-500 pt-2 border-t border-zinc-800/80">
        <div className="flex items-center space-x-5">
          <span className="flex items-center space-x-1.5">
            <span className="w-3 h-0.5 bg-zinc-300 inline-block" />
            <span>Active Link</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <span className="w-3 h-0.5 bg-zinc-600 inline-block border-t border-dashed" />
            <span>Standby Link</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <span className="w-3 h-0.5 bg-rose-500 inline-block border-t border-dashed" />
            <span>Severed Link</span>
          </span>
        </div>
        <span>Select node to view metrics</span>
      </div>
    </div>
  );
};