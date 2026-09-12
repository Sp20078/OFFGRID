'use client';

import React from 'react';
import { Wifi, WifiOff, ShieldCheck, Activity } from 'lucide-react';

interface HeaderProps {
  internetOnline: boolean;
  onToggleInternet: () => void;
}

export const Header: React.FC<HeaderProps> = ({ internetOnline, onToggleInternet }) => {
  return (
    <header className="w-full bg-slate-950 border-b border-slate-800 px-6 py-3 flex items-center justify-between">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 rounded-full bg-cyan-500 animate-pulse" />
          <h1 className="font-mono text-xl font-bold tracking-wider text-slate-100 uppercase">
            OFFGRID <span className="text-cyan-400 text-xs font-normal border border-cyan-500/30 bg-cyan-950/50 px-2 py-0.5 rounded">NOC CONTROL</span>
          </h1>
        </div>
        <div className="h-4 w-[1px] bg-slate-800" />
        <div className="flex items-center space-x-1 text-xs font-mono text-slate-400">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>DECENTRALIZED MESH PROTOCOL</span>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <button
          onClick={onToggleInternet}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded text-xs font-mono border transition-all ${
            internetOnline
              ? 'bg-slate-900 border-emerald-500/40 text-emerald-400 hover:bg-emerald-950/30'
              : 'bg-red-950/40 border-red-500/50 text-red-400 animate-pulse'
          }`}
        >
          {internetOnline ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
          <span>WAN CONNECTION: {internetOnline ? 'ACTIVE' : 'OFFLINE (P2P MODE)'}</span>
        </button>

        <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded text-xs font-mono text-cyan-400">
          <Activity className="w-3.5 h-3.5 animate-spin text-cyan-400" />
          <span>P2P CORE: ACTIVE</span>
        </div>
      </div>
    </header>
  );
};