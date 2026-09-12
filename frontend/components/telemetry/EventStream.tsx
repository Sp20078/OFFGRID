'use client';

import React, { useState } from 'react';
import { NetworkLog } from '@/types/network';

interface EventStreamProps {
  logs: NetworkLog[];
}

export const EventStream: React.FC<EventStreamProps> = ({ logs }) => {
  const [filter, setFilter] = useState<'ALL' | 'ERROR' | 'WARN' | 'SUCCESS'>('ALL');

  const filteredLogs = logs.filter(log => {
    if (filter === 'ALL') return true;
    return log.level === filter;
  });

  const getBadgeStyle = (level: NetworkLog['level']) => {
    switch (level) {
      case 'ERROR':
        return 'bg-rose-950/50 text-rose-400 border border-rose-800/60';
      case 'WARN':
        return 'bg-amber-950/50 text-amber-400 border border-amber-800/60';
      case 'SUCCESS':
        return 'bg-emerald-950/50 text-emerald-400 border border-emerald-800/60';
      default:
        return 'bg-zinc-800 text-zinc-400 border border-zinc-700/60';
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-4 font-mono select-none py-2">
      {/* Log Screen Header */}
      <div className="p-5 rounded-lg bg-zinc-900/40 border border-zinc-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-sm font-bold text-zinc-100 uppercase tracking-wide">
            Audit Log Stream
          </h2>
          <p className="text-zinc-400 text-xs mt-1">
            Real-time verification log of peer discovery, path recalculations, and payload hops.
          </p>
        </div>

        {/* Filter Chips */}
        <div className="flex items-center space-x-1.5 bg-zinc-950 p-1 rounded-md border border-zinc-800 text-xs">
          {(['ALL', 'ERROR', 'WARN', 'SUCCESS'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-all cursor-pointer ${
                filter === f
                  ? 'bg-zinc-800 text-zinc-100'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Terminal Viewport */}
      <div className="p-4 rounded-lg bg-zinc-950 border border-zinc-800 min-h-[460px] max-h-[600px] overflow-y-auto space-y-2 text-xs">
        {filteredLogs.length === 0 ? (
          <div className="text-zinc-600 text-center py-16">No events matching filter.</div>
        ) : (
          filteredLogs.map(log => (
            <div
              key={log.id}
              className="flex items-start space-x-3 py-1.5 px-2 rounded hover:bg-zinc-900/40 transition-colors border-b border-zinc-900/40"
            >
              <span
                className="text-zinc-500 text-[11px] shrink-0 select-none font-mono"
                suppressHydrationWarning
              >
                {log.timestamp}
              </span>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded font-bold shrink-0 ${getBadgeStyle(
                  log.level
                )}`}
              >
                {log.level}
              </span>
              <span className="text-zinc-300 font-mono leading-relaxed">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};