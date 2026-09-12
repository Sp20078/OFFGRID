'use client';

import {
  useEffect,
  useState,
} from 'react';

import { useNetworkState } from '@/hooks/useNetworkState';

export default function CustomMessageBox() {
  const {
    nodes,
    loading,
    transferState,
    error,
    actions,
  } = useNetworkState();

  const destinations =
    nodes.filter(
      (node) => node.id !== 'NODE_A',
    );

  const [destination, setDestination] =
    useState('');

  const [message, setMessage] =
    useState('');

  const [sending, setSending] =
    useState(false);

  useEffect(() => {
    if (destinations.length === 0) {
      setDestination('');
      return;
    }

    if (
      destinations.some(
        (node) =>
          node.id === destination,
      )
    ) {
      return;
    }

    const preferred =
      destinations.find(
        (node) =>
          node.id === 'NODE_E',
      );

    setDestination(
      preferred?.id ??
        destinations[0]?.id ??
        '',
    );
  }, [nodes, destination]);

  const handleSend =
    async () => {
      const cleanMessage =
        message.trim();

      if (!cleanMessage) {
        return;
      }

      if (!destination) {
        return;
      }

      setSending(true);

      try {
        const success =
          await actions.sendCustomMessage(
            cleanMessage,
            destination,
            'NODE_A',
          );

        if (success) {
          setMessage('');
        }
      } finally {
        setSending(false);
      }
    };

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
      <div className="mb-5">
        <h2 className="text-sm font-semibold text-white">
          Send P2P Message
        </h2>

        <p className="mt-1 text-xs text-white/40">
          Send any custom message through OFFGRID.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label
            htmlFor="offgrid-destination"
            className="mb-2 block text-xs font-medium text-white/60"
          >
            Destination
          </label>

          <select
            id="offgrid-destination"
            value={destination}
            onChange={(event) =>
              setDestination(
                event.target.value,
              )
            }
            disabled={
              loading ||
              sending ||
              destinations.length === 0
            }
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-white outline-none focus:border-white/30"
          >
            {destinations.length === 0 ? (
              <option value="">
                No destinations
              </option>
            ) : (
              destinations.map(
                (node) => (
                  <option
                    key={node.id}
                    value={node.id}
                    className="bg-black"
                  >
                    {node.label ??
                      node.id}
                    {node.status ===
                    'OFFLINE'
                      ? ' — OFFLINE'
                      : ''}
                  </option>
                ),
              )
            )}
          </select>
        </div>

        <div>
          <label
            htmlFor="offgrid-message"
            className="mb-2 block text-xs font-medium text-white/60"
          >
            Message
          </label>

          <textarea
            id="offgrid-message"
            value={message}
            maxLength={500}
            rows={5}
            disabled={
              loading || sending
            }
            onChange={(event) =>
              setMessage(
                event.target.value,
              )
            }
            onKeyDown={(event) => {
              if (
                event.key === 'Enter' &&
                event.ctrlKey
              ) {
                event.preventDefault();

                void handleSend();
              }
            }}
            placeholder="Type your custom message..."
            className="w-full resize-none rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-white outline-none placeholder:text-white/25 focus:border-white/30"
          />

          <div className="mt-2 flex justify-between text-[11px] text-white/30">
            <span>
              Ctrl + Enter to send
            </span>

            <span>
              {message.length}/500
            </span>
          </div>
        </div>

        <button
          type="button"
          onClick={() =>
            void handleSend()
          }
          disabled={
            loading ||
            sending ||
            transferState.isTransferring ||
            !message.trim() ||
            !destination
          }
          className="w-full rounded-xl bg-white px-4 py-3 text-sm font-semibold text-black transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {sending
            ? 'Sending...'
            : 'Send P2P Message'}
        </button>

        {error && (
          <div className="rounded-xl border border-red-400/20 bg-red-400/5 px-3 py-2 text-xs text-red-300">
            {error}
          </div>
        )}
      </div>
    </section>
  );
}