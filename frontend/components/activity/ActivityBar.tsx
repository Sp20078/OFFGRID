'use client';

import React, { useState } from 'react';
import { TransferState, MeshNode } from '@/types/network';

interface ActivityBarProps {
  onSendMessage: () => void;
  onSendFile: () => void;
  transferState: TransferState;
  nodes: MeshNode[];
  liveMode: boolean;
  sendingMessage: boolean;
  onSendCustomMessage: (destination: string, payload: string) => Promise<boolean>;
}

export const ActivityBar: React.FC<ActivityBarProps> = ({
  onSendMessage,
  onSendFile,
  transferState,
  nodes,
  liveMode,
  sendingMessage,
  onSendCustomMessage
}) => {
  const { isTransferring, transferType, transferProgress, messageQueue } = transferState;

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
            : 'Inject encrypted text broadcasts or multi-chunk binary files across the decentralized mesh.'}
        </p>

        {/* Live Transfer Status Bar */}
        <div className="mt-5 p-4 rounded bg-zinc-950/80 border border-zinc-800/80 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-zinc-300 font-medium">
              {sendingMessage
                ? 'Transmitting P2P Message...'
                : isTransferring
                  ? `Transmitting ${transferType === 'FILE' ? 'Binary File Chunks' : 'P2P Message'}...`
                  : 'Radio Transmitter Idle'}
            </span>
            <span className="text-zinc-400 font-semibold">
              {sendingMessage ? '—' : `${transferProgress}%`}
            </span>
          </div>

          {/* Clean Progress Track */}
          <div className="w-full h-2 bg-zinc-900 rounded-full border border-zinc-800 overflow-hidden">
            <div
              className="h-full bg-zinc-100 transition-all duration-200 rounded-full"
              style={{ width: `${sendingMessage ? 100 : transferProgress}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-[11px] text-zinc-500 pt-1">
            <span>In-flight Queue: {sendingMessage ? 1 : messageQueue} packet(s)</span>
            <span>Protocols: {liveMode ? 'UDP / OFFGRID Mesh' : 'E2EE / Ed25519 Signed'}</span>
          </div>
        </div>
      </div>

      {/* REAL MODE: Custom Message Composer */}
      <div className="p-5 rounded-lg bg-zinc-900/40 border border-zinc-800">
        <div className="font-bold text-zinc-100 text-sm">Custom Message</div>
        <p className="text-zinc-400 text-xs mt-1.5 leading-relaxed">
          {liveMode
            ? 'Type any text and send it from this node to a discovered peer over the real LAN.'
            : 'Requires REAL LAN MODE — set NEXT_PUBLIC_OFFGRID_API to your node API (e.g. http://localhost:8001) and restart the dashboard.'}
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

      {/* Action Cards (simulation mode) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        {/* Send Message */}
        <div className="p-5 rounded-lg bg-zinc-900/40 border border-zinc-800 flex flex-col justify-between">
          <div>
            <div className="font-bold text-zinc-100 text-sm">Encrypted Message</div>
            <p className="text-zinc-400 text-xs mt-1.5 leading-relaxed">
              Injects a 128-byte broadcast telemetry frame from Node A (Origin) to Node E (Target).
            </p>
          </div>
          <div className="mt-5">
            <button
              onClick={onSendMessage}
              disabled={isTransferring}
              className={`w-full py-2.5 rounded text-xs font-semibold border transition-all ${
                isTransferring
                  ? 'bg-zinc-900 border-zinc-800 text-zinc-600 cursor-not-allowed'
                  : 'bg-zinc-800 border-zinc-700 text-zinc-100 hover:bg-zinc-700 cursor-pointer'
              }`}
            >
              {isTransferring && transferType === 'MESSAGE' ? 'Broadcasting...' : 'Send P2P Message'}
            </button>
          </div>
        </div>

        {/* Send File */}
        <div className="p-5 rounded-lg bg-zinc-900/40 border border-zinc-800 flex flex-col justify-between">
          <div>
            <div className="font-bold text-zinc-100 text-sm">Chunked File Transfer</div>
            <p className="text-zinc-400 text-xs mt-1.5 leading-relaxed">
              Transmits binary data with SHA-256 chunk validation and Store & Forward fallback caching.
            </p>
          </div>
          <div className="mt-5">
            <button
              onClick={onSendFile}
              disabled={isTransferring}
              className={`w-full py-2.5 rounded text-xs font-semibold border transition-all ${
                isTransferring
                  ? 'bg-zinc-900 border-zinc-800 text-zinc-600 cursor-not-allowed'
                  : 'bg-zinc-800 border-zinc-700 text-zinc-100 hover:bg-zinc-700 cursor-pointer'
              }`}
            >
              {isTransferring && transferType === 'FILE' ? 'Transmitting Chunks...' : 'Send File Chunk'}
            </button>
          </div>
        </div>
      </div>

      {/* Delay-Tolerant Networking (DTN) Note */}
      <div className="p-4 rounded-lg bg-zinc-900/30 border border-zinc-800/80 text-xs text-zinc-400 flex items-center justify-between">
        <div>
          <span className="font-semibold text-zinc-200">Delay-Tolerant Networking (DTN):</span>
          <span className="ml-1 text-zinc-400">
            If the target destination is offline, relay nodes hold packets in local RAM and forward upon reconnection.
          </span>
        </div>
        <span className="text-amber-400 font-medium shrink-0 ml-4">
          Store & Forward Queue: {metrics_queue(nodes)} pkt(s)
        </span>
      </div>
    </div>
  );
};

function metrics_queue(nodes: MeshNode[]): number {
  return nodes.reduce((acc, n) => acc + (n.storedPacketsCount || 0), 0);
}
