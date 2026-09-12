'use client';

import React from 'react';
import { MeshNode } from '@/types/network';
import { MessageTrackedEvent } from '@/hooks/useNetworkState';

interface LiveStatusProps {
  nodes: MeshNode[];
  messageEvents: MessageTrackedEvent[];
  liveMode: boolean;
}

const STATUS_ICON: Record<MessageTrackedEvent['status'], string> = {
  PENDING: '⏳',
  FORWARDED: '📡',
  DELIVERED: '✅',
  FAILED: '❌',
  RECEIVED: '📥',
};

const STATUS_STYLE: Record<MessageTrackedEvent['status'], string> = {
  PENDING: 'bg-amber-950/50 text-amber-400 border border-amber-800/60',
  FORWARDED: 'bg-sky-950/50 text-sky-400 border border-sky-800/60',
  DELIVERED: 'bg-emerald-950/50 text-emerald-400 border border-emerald-800/60',
  FAILED: 'bg-rose-950/50 text-rose-400 border border-rose-800/60',
  RECEIVED: 'bg-violet-950/50 text-violet-300 border border-violet-800/60',
};

export const LiveStatus: React.FC<LiveStatusProps> = ({
  nodes,
  messageEvents,
  liveMode,
}) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* NODE ACTIVATION */}
      <div className="p-5 rounded-lg bg-zinc-900/40 border border-zinc-800">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-zinc-100 uppercase tracking-wide">
            Node Status
          </h3>
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded font-medium border ${
              liveMode
                ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800/50'
                : 'bg-amber-950/40 text-amber-400 border-amber-800/50'
            }`}
          >
            {liveMode ? '● LIVE' : '○ SIMULATION'}
          </span>
        </div>

        <div className="mt-4 space-y-2">
          {nodes.map(node => (
            <div
              key={node.id}
              className="flex items-center justify-between px-3 py-2 rounded bg-zinc-950/80 border border-zinc-800/80"
            >
              <div className="flex items-center space-x-2.5">
                <span
                  className={`w-2 h-2 rounded-full ${
                    node.status === 'ONLINE'
                      ? 'bg-emerald-400 animate-pulse'
                      : 'bg-zinc-600'
                  }`}
                />
                <span className="text-xs font-semibold text-zinc-100">{node.id}</span>
                <span className="text-[10px] text-zinc-500">{node.ip}</span>
              </div>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                  node.status === 'ONLINE'
                    ? 'bg-emerald-950/50 text-emerald-400'
                    : 'bg-zinc-800/80 text-zinc-500'
                }`}
              >
                {node.status === 'ONLINE' ? 'ACTIVATED' : 'OFFLINE'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* MESSAGE LIFECYCLE */}
      <div className="p-5 rounded-lg bg-zinc-900/40 border border-zinc-800">
        <h3 className="text-sm font-bold text-zinc-100 uppercase tracking-wide">
          Message Tracker
        </h3>

        <div className="mt-4 space-y-2 max-h-[280px] overflow-y-auto">
          {messageEvents.length === 0 ? (
            <div className="text-zinc-600 text-xs text-center py-10">
              No messages yet — send one from the Transfers tab.
            </div>
          ) : (
            messageEvents.map(event => (
              <div
                key={event.id}
                className="px-3 py-2 rounded bg-zinc-950/80 border border-zinc-800/80 space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-300 font-semibold">
                    {event.status === 'RECEIVED'
                      ? `${event.source} → this node`
                      : `this node → ${event.destination}`}
                  </span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${STATUS_STYLE[event.status]}`}
                  >
                    {STATUS_ICON[event.status]} {event.status}
                    {event.status === 'RECEIVED' && event.hopCount ? ` (${event.hopCount} hop${event.hopCount > 1 ? 's' : ''})` : ''}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-zinc-400 truncate max-w-[70%]">
                    &ldquo;{event.text}&rdquo;
                  </span>
                  <span className="text-[10px] text-zinc-600 shrink-0">{event.timestamp}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
