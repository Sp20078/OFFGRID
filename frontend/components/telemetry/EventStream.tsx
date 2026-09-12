'use client';

import React from 'react';
import { NetworkLog } from '@/types/network';
import { Terminal } from 'lucide-react';

interface EventStreamProps {
  logs: NetworkLog[];
}

const COLOR_MAP: Record<NetworkLog['level'], string> = {
  INFO: 'text-slate-400',
  WARN: 'text-amber-400 bg-amber-950/20 px-1 rounded',
  ERROR: 'text-red-400 bg-red-950/30 px-1 rounded font-bold',
  SUCCESS: 'text-emerald-400 font-semibold'
};

export const EventStream: React.FC<EventStreamProps> = ({ logs }) => {
  return (
    <div className="w-full h-full bg-slate-950 border border-slate-800 rounded-lg p-4 flex flex-col font-mono text-xs">
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 text-slate-400">
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <span className="font-bold text-slate-200 uppercase">Live Event Telemetry</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1 max-h-[460px]">
        {logs.map(log => (
          <div key={log.id} className="leading-relaxed border-b border-slate-900/60 pb-1.5 flex space-x-2">
            <span className="text-slate-600 select-none">[{log.timestamp}]</span>
            <span className={COLOR_MAP[log.level]}>{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
};