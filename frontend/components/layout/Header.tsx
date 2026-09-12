'use client';

import React from 'react';

export type NavTab = 'network' | 'transfers' | 'logs';

interface HeaderProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  internetOnline: boolean;
  onToggleInternet: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  internetOnline,
  onToggleInternet
}) => {
  const tabs: { id: NavTab; label: string }[] = [
    { id: 'network', label: 'Topology & Simulator' },
    { id: 'transfers', label: 'Transfers' },
    { id: 'logs', label: 'Audit Logs' }
  ];

  return (
    <header className="w-full bg-zinc-950 border-b border-zinc-800/80 px-6 py-2.5 flex items-center justify-between font-mono select-none sticky top-0 z-50">
      {/* Brand & Navigation */}
      <div className="flex items-center space-x-8">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-bold tracking-wider text-zinc-100">OFFGRID</span>
          <span className="text-[10px] uppercase text-zinc-500 tracking-widest border border-zinc-800 px-1.5 py-0.5 rounded">
            NOC
          </span>
        </div>

        {/* Clean Top-Level Tabs */}
        <nav className="flex items-center space-x-1 bg-zinc-900/80 p-1 rounded-md border border-zinc-800/80 text-xs">
          {tabs.map(tab => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`px-3 py-1 rounded transition-all cursor-pointer font-medium ${
                  isActive
                    ? 'bg-zinc-800 text-zinc-100 shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Right Controls: Minimalist Status Indicators */}
      <div className="flex items-center space-x-3 text-xs">
        <div className="flex items-center space-x-1.5 text-zinc-400 px-2.5 py-1 rounded bg-zinc-900/60 border border-zinc-800/60">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span className="text-[11px] text-zinc-300">P2P Core Active</span>
        </div>

        <button
          onClick={onToggleInternet}
          title="Toggle WAN Gateway connection"
          className={`flex items-center space-x-1.5 px-2.5 py-1 rounded text-[11px] font-medium border transition-all cursor-pointer ${
            internetOnline
              ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-400 hover:bg-emerald-900/30'
              : 'bg-amber-950/30 border-amber-500/40 text-amber-300 hover:bg-amber-900/30'
          }`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${internetOnline ? 'bg-emerald-400' : 'bg-amber-400'}`} />
          <span>WAN: {internetOnline ? 'ONLINE' : 'OFFLINE'}</span>
        </button>
      </div>
    </header>
  );
};