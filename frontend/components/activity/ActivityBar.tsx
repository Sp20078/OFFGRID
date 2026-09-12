'use client';

import React from 'react';
import { TransferState, MeshNode } from '@/types/network';

interface ActivityBarProps {
  onSendMessage: () => void;
  onSendFile: () => void;
  transferState: TransferState;
  nodes: MeshNode[];
}

export const ActivityBar: React.FC<ActivityBarProps> = ({
  onSendMessage,
  onSendFile,
  transferState,
  nodes
}) => {
  const { isTransferring, transferType, transferProgress, messageQueue } = transferState;
  const nodeD = nodes.find(n => n.id === 'NODE_D');
  const isNodeEOffline = nodes.find(n => n.id === 'NODE_E')?.status === 'OFFLINE';

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 font-mono select-none py-2">
      {/* Screen Header */}
      <div className="p-5 rounded-lg bg-zinc-900/40 border border-zinc-800">
        <h2 className="text-sm font-bold text-zinc-100 uppercase tracking-wide">
          Payload Transfer & Delivery
        </h2>
        <p className="text-zinc-400 text-xs mt-1">
          Inject encrypted text broadcasts or multi-chunk binary files across the decentralized mesh.
        </p>

        {/* Live Transfer Status Bar */}
        <div className="mt-5 p-4 rounded bg-zinc-950/80 border border-zinc-800/80 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-zinc-300 font-medium">
              {isTransferring
                ? `Transmitting ${transferType === 'FILE' ? 'Binary File Chunks' : 'P2P Message'}...`
                : 'Radio Transmitter Idle'}
            </span>
            <span className="text-zinc-400 font-semibold">{transferProgress}%</span>
          </div>

          {/* Clean Progress Track */}
          <div className="w-full h-2 bg-zinc-900 rounded-full border border-zinc-800 overflow-hidden">
            <div
              className="h-full bg-zinc-100 transition-all duration-200 rounded-full"
              style={{ width: `${transferProgress}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-[11px] text-zinc-500 pt-1">
            <span>In-flight Queue: {messageQueue} packet(s)</span>
            <span>Protocols: E2EE / Ed25519 Signed</span>
          </div>
        </div>
      </div>

      {/* Action Cards */}
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
        {isNodeEOffline && (
          <span className="text-amber-400 font-medium shrink-0 ml-4">
            Node D Buffer: {nodeD?.storedPacketsCount || 0} pkt(s)
          </span>
        )}
      </div>
    </div>
  );
};
