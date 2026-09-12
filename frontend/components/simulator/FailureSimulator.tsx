'use client';

import React from 'react';
import { Zap, RefreshCw, WifiOff } from 'lucide-react';

interface FailureSimulatorProps {
  onTriggerNodeC: () => void;
  onToggleInternet: () => void;
  onReset: () => void;
  internetOnline: boolean;
  isNodeCOffline?: boolean;
}

export const FailureSimulator: React.FC<FailureSimulatorProps> = ({
  onTriggerNodeC,
  onToggleInternet,
  onReset,
  internetOnline,
  isNodeCOffline = false
}) => {
  return (
    <div className="w-full bg-slate-900/90 border border-slate-800 rounded-lg p-4 font-mono">
      <div className="text-xs font-bold text-slate-300 uppercase mb-3 flex items-center space-x-2">
        <Zap className="w-4 h-4 text-amber-400" />
        <span>Demo Scenario Simulator</span>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <button
          onClick={onToggleInternet}
          className="flex items-center justify-center space-x-2 p-2.5 rounded text-xs border border-amber-500/30 bg-amber-950/20 text-amber-300 hover:bg-amber-900/40 transition-all cursor-pointer"
        >
          <WifiOff className="w-3.5 h-3.5" />
          <span>{internetOnline ? '1. Sever WAN' : 'Restore WAN'}</span>
        </button>

        <button
          onClick={onTriggerNodeC}
          disabled={isNodeCOffline}
          className={`flex items-center justify-center space-x-2 p-2.5 rounded text-xs border font-bold transition-all ${
            isNodeCOffline
              ? 'border-slate-800 bg-slate-950 text-slate-500 cursor-not-allowed'
              : 'border-red-500/40 bg-red-950/30 text-red-300 hover:bg-red-900/50 cursor-pointer'
          }`}
        >
          <Zap className={`w-3.5 h-3.5 ${isNodeCOffline ? 'text-slate-600' : 'text-red-400'}`} />
          <span>{isNodeCOffline ? 'Node C Severed' : '2. Fail Node C'}</span>
        </button>

        <button
          onClick={onReset}
          className="flex items-center justify-center space-x-2 p-2.5 rounded text-xs border border-slate-700 bg-slate-950 text-slate-400 hover:text-slate-200 transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Reset Network</span>
        </button>
      </div>
    </div>
  );
};