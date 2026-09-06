import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createApiService, type ApiService } from '../../services/apiService';
import { toWebSocketUrl } from '../../services/apiUrl';
import {
  connectSessionSocket,
  type SessionSocket,
} from '../../services/websocketService';
import { useConnectionStore, useSessionsStore } from '../../store';
import type { ConnectionStatus, SessionId } from '../../types';
import { useSessionMutations } from './useSessionMutations';

/**
 * Loads one session and keeps it live over the WebSocket channel.
 *
 * The socket follows the session id and current API origin. Keying it on
 * the snapshot would tear down and re-open the connection on every incoming
 * event, which is the classic way to turn a realtime feed into a reconnect
 * storm.
 */
export function useSessionDetail(sessionId: SessionId, service?: ApiService) {
  const apiUrl = useConnectionStore((state) => state.apiUrl);
  const beginActive = useSessionsStore((state) => state.beginActive);
  const setActive = useSessionsStore((state) => state.setActive);
  const setRecovery = useSessionsStore((state) => state.setRecovery);
  const clear = useSessionsStore((state) => state.clear);

  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<string | null>(null);

  const api = useMemo(
    () => service ?? (apiUrl ? createApiService(apiUrl) : null),
    [service, apiUrl],
  );

  // A new connection owns the shared active slot. An older mounted screen may
  // finish later, but cannot write to or clear a newer screen's selection.
  const connection = useMemo(
    () => ({ api, apiUrl, sessionId, token: Symbol(sessionId) }),
    [api, apiUrl, sessionId],
  );
  const session = useSessionsStore((state) =>
    state.activeOwner === connection.token ? state.active : null,
  );
  const latestRead = useRef(0);
  const negotiated = useRef(false);
  const terminal = useRef(false);
  const socketRef = useRef<SessionSocket | null>(null);
  const ownsActive = useCallback(
    () => useSessionsStore.getState().activeOwner === connection.token,
    [connection],
  );
  const load = useCallback(async () => {
    if (!connection.api || !ownsActive() || negotiated.current) return;
    const request = ++latestRead.current;
    const current = () =>
      ownsActive() && request === latestRead.current && !negotiated.current;
    setError(null);
    try {
      const snapshot = await connection.api.getSession(connection.sessionId);
      if (!current()) return;
      setActive(connection.token, snapshot);
      setError(null);
    } catch {
      if (current()) setError('Could not load this session.');
    }
  }, [connection, ownsActive, setActive]);

  useEffect(() => {
    beginActive(connection.token);
    negotiated.current = false;
    terminal.current = false;
    setStatus('disconnected');
    setError(null);
    void load();
    return () => {
      latestRead.current += 1;
      clear(connection.token);
    };
  }, [connection, beginActive, load, clear]);

  useEffect(() => {
    if (!apiUrl) return;
    let live = true;
    const socket = connectSessionSocket(toWebSocketUrl(apiUrl), sessionId, {
      onRecovery: (recovery) => {
        if (!live || !ownsActive()) return;
        if (!negotiated.current && recovery.status !== 'connecting') {
          negotiated.current = true;
          latestRead.current += 1;
        }
        setRecovery(connection.token, recovery);
        if (
          recovery.status === 'deleted' ||
          recovery.status === 'unsupported'
        ) {
          terminal.current = true;
          setError(
            recovery.status === 'deleted'
              ? 'This session no longer exists.'
              : 'This server is incompatible with this app. Update the server to continue.',
          );
        } else if (
          recovery.status === 'live' ||
          recovery.status === 'buffering'
        )
          setError(null);
      },
      onStatusChange: (next) => {
        if (live && ownsActive()) setStatus(next);
      },
    });
    socketRef.current = socket;
    return () => {
      live = false;
      if (socketRef.current === socket) socketRef.current = null;
      socket.close();
    };
  }, [apiUrl, sessionId, connection, ownsActive, setRecovery]);

  const reload = useCallback(() => {
    if (!ownsActive() || terminal.current || !socketRef.current) return;
    latestRead.current += 1;
    negotiated.current = true;
    setError(null);
    socketRef.current.reload();
  }, [ownsActive]);

  const canMutate = useCallback(
    () =>
      ownsActive() &&
      !terminal.current &&
      useSessionsStore.getState().active !== null,
    [ownsActive],
  );
  const mutations = useSessionMutations(connection, canMutate);

  return { session, status, error, ...mutations, reload };
}
