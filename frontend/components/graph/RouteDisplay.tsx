'use client';

import React from 'react';
import { ChevronRight, ArrowRightLeft } from 'lucide-react';

interface RouteDisplayProps {
  activeRoute: string[];
}

export const RouteDisplay: React.FC<RouteDisplayProps> = ({ activeRoute }) => {
  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-lg p-3 flex items-center justify-between font-mono">
      <div className="flex items-center space-x-2 text-xs text-slate-400">
        <ArrowRightLeft className="w-4 h-4 text-cyan-400" />
        <span className="font-bold text-slate-200 uppercase">Current Computed Route:</span>
      </div>

      <div className="flex items-center space-x-2">
        {activeRoute.map((nodeId, idx) => {
          const isLast = idx === activeRoute.length - 1;
          return (
            <React.Fragment key={nodeId}>
              <span className="px-2.5 py-1 bg-slate-950 border border-cyan-500/40 text-cyan-300 rounded text-xs font-bold tracking-wide">
                {nodeId}
              </span>
              {!isLast && <ChevronRight className="w-4 h-4 text-slate-600 animate-pulse" />}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};