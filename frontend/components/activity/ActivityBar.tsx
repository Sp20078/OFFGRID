'use client';

import React, { useState } from 'react';
import { MeshNode } from '@/types/network';

interface ActivityBarProps {
  nodes: MeshNode[];
  liveMode: boolean;
  sendingMessage: boolean;
  onSendCustomMessage: (destination: string, payload: string) => Promise<boolean>;
}

export const ActivityBar: React.FC<ActivityBarProps> = ({
  nodes,
  liveMode,
  sendingMessage,
  onSendCustomMessage
}) => {
  const [customText, setCustomText] = useState('');
  const [customDest, setCustomDest] = useState('NODE_B');
  const [customStatus, setCustomStatus] = useState<string | null>(null);

  const onlineNodes = nodes.filter(n => n.status === 'ONLINE');
  const destinations = onlineNodes.map(n => n.id);
  if (!destinations.includes(customDest)) {
    setCustomDest(destinations[0] ?? 'NODE_B');
  }

  const submitCustomMessage = async () => {
    const text = customText.trim();
    if (!text || sendingMessage) return;

    setCustomStatus(null);
    const ok = await onSendCustomMessage(customDest, text);

    if (ok) {
      setCustomText('');
      setCustomStatus('SENT — waiting for ACK from destination');
      setTimeout(() => setCustomStatus(null), 4000);
    } else {
      setCustomStatus('SEND FAILED — check node API and destination');
      setTimeout(() => setCustomStatus(null), 6000);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 font-mono select-none py-2">
      {/* Screen Header */}
      <div className="p-5 rounded-lg bg-zinc-900/40 border border-zinc-800">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-zinc-100 uppercase tracking-wide">
            Payload Transfer & Delivery
          </h2>
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded font-medium border ${
              liveMode
                ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800/50'
                : 'bg-amber-950/40 text-amber-400 border-amber-800/50'
            }`}
          >
            {liveMode ? 'REAL LAN MODE — LIVE NODE' : 'SIMULATION MODE'}
          </span>
        </div>
        <p className="text-zinc-400 text-xs mt-1">
          {liveMode
            ? 'Messages below are transmitted as real UDP packets to the connected OFFGRID node.'
            : 'Requires REAL LAN MODE — set NEXT_PUBLIC_OFFGRID_API to your node API (e.g. http://localhost:8001) and restart the dashboard.'}
        </p>
      </div>

      {/* Custom Message Composer */}
      <div className="p-5 rounded-lg bg-zinc-900/40 border border-zinc-800">
        <div className="font-bold text-zinc-100 text-sm">Custom Message</div>
        <p className="text-zinc-400 text-xs mt-1.5 leading-relaxed">
          {liveMode
            ? 'Type any text and send it from this node to a discovered peer over the real LAN.'
            : 'The dashboard could not reach a live node. Start the node with --api-port and set NEXT_PUBLIC_OFFGRID_API.'}
        </p>

        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <label className="text-zinc-400" htmlFor="offgrid-destination">
              Destination:
            </label>
            <select
              id="offgrid-destination"
              value={customDest}
              onChange={e => setCustomDest(e.target.value)}
              className="px-2 py-1.5 rounded bg-zinc-950 border border-zinc-700 text-zinc-100 focus:outline-none focus:border-zinc-500"
            >
              {(destinations.length ? destinations : ['NODE_B', 'NODE_C', 'NODE_D', 'NODE_E']).map(id => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
          </div>

          <textarea
            value={customText}
            onChange={e => setCustomText(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                submitCustomMessage();
              }
            }}
            placeholder="Hello from Laptop 1"
            rows={3}
            maxLength={5000}
            className="w-full px-3 py-2 rounded bg-zinc-950 border border-zinc-700 text-zinc-100 text-xs placeholder-zinc-600 focus:outline-none focus:border-zinc-500 resize-none"
          />

          <div className="flex items-center justify-between gap-3">
            <span className="text-[11px] text-zinc-500">
              {customStatus ?? `${customText.length}/5000 chars · Ctrl+Enter to send`}
            </span>
            <button
              onClick={submitCustomMessage}
              disabled={sendingMessage || !customText.trim()}
              className={`px-4 py-2 rounded text-xs font-semibold border transition-all ${
                sendingMessage || !customText.trim()
                  ? 'bg-zinc-900 border-zinc-800 text-zinc-600 cursor-not-allowed'
                  : 'bg-zinc-100 border-zinc-100 text-zinc-950 hover:bg-white cursor-pointer'
              }`}
            >
              {sendingMessage ? 'Sending...' : 'Send Message'}
            </button>
          </div>
        </div>
      </div>

      {/* Delay-Tolerant Networking (DTN) Note */}
      <div className="p-4 rounded-lg bg-zinc-900/30 border border-zinc-800/80 text-xs text-zinc-400">
        <span className="font-semibold text-zinc-200">Delay-Tolerant Networking (DTN):</span>
        <span className="ml-1">
          If the destination is offline, relay nodes hold packets in local RAM and forward upon reconnection.
          Status of every message appears live in the Message Tracker on the Topology tab.
        </span>
      </div>
    </div>
  );
};
