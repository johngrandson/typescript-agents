import { applySessionRecoveryEvent, createSessionRecovery } from './types';
import type { RealtimeStatus, SessionRecoveryState } from './types';
import {
  isSessionEvent,
  isSessionEventV2,
  registerContractFormats,
} from './types/validators';

/** A caller owns this stream and every retry until close or terminal recovery. */
export interface SessionStream {
  close(): void;
  reload(): void;
}

const INITIAL_DELAY_MS = 500;
const MAX_DELAY_MS = 15_000;
const BOOTSTRAP_TIMEOUT_MS = 10_000;

/** Fresh EventSources deliberately replace native reconnects so every attempt bootstraps. */
export function connectSessionStream(
  sessionId: string,
  handlers: {
    onRecovery: (state: SessionRecoveryState) => void;
    onStatusChange: (status: RealtimeStatus) => void;
  },
): SessionStream {
  registerContractFormats();
  let source: EventSource | null = null;
  let generation = 0;
  let stopped = false;
  let delay = INITIAL_DELAY_MS;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let bootstrapTimer: ReturnType<typeof setTimeout> | null = null;

  function clearBootstrap(): void {
    if (bootstrapTimer !== null) clearTimeout(bootstrapTimer);
    bootstrapTimer = null;
  }
  function release(): void {
    generation++;
    clearBootstrap();
    const previous = source;
    source = null;
    if (!previous) return;
    previous.onopen = null;
    previous.onmessage = null;
    previous.onerror = null;
    previous.close();
  }
  function stop(): void {
    stopped = true;
    window.removeEventListener('offline', offline);
    window.removeEventListener('online', reload);
    if (retryTimer !== null) clearTimeout(retryTimer);
    retryTimer = null;
    release();
  }
  function retry(status: RealtimeStatus): void {
    if (stopped) return;
    release();
    handlers.onStatusChange(status);
    if (stopped || retryTimer !== null || !navigator.onLine) return;
    retryTimer = setTimeout(() => {
      retryTimer = null;
      open();
    }, delay);
    delay = Math.min(delay * 2, MAX_DELAY_MS);
  }
  function offline(): void {
    if (stopped) return;
    if (retryTimer !== null) clearTimeout(retryTimer);
    retryTimer = null;
    release();
    handlers.onStatusChange('error');
  }
  function reload(): void {
    if (stopped) return;
    if (!navigator.onLine) {
      offline();
      return;
    }
    if (retryTimer !== null) clearTimeout(retryTimer);
    retryTimer = null;
    delay = INITIAL_DELAY_MS;
    retry('connecting');
  }
  function open(): void {
    if (stopped) return;
    if (!navigator.onLine) {
      offline();
      return;
    }
    const attempt = ++generation;
    const current = () => !stopped && generation === attempt;
    let recovery = createSessionRecovery(sessionId);
    handlers.onRecovery(recovery);
    handlers.onStatusChange('connecting');
    if (!current()) return;
    let native: EventSource;
    try {
      native = new EventSource(
        `/api/sessions/${encodeURIComponent(sessionId)}/events?protocol=2`,
      );
    } catch {
      retry('error');
      return;
    }
    source = native;
    bootstrapTimer = setTimeout(() => {
      if (current()) retry('error');
    }, BOOTSTRAP_TIMEOUT_MS);
    native.onmessage = (message: MessageEvent) => {
      if (!current()) return;
      if (typeof message.data !== 'string') {
        retry('error');
        return;
      }
      let value: unknown;
      try {
        value = JSON.parse(message.data);
      } catch {
        retry('error');
        return;
      }
      if (
        !isSessionEventV2(value) &&
        !(isSessionEvent(value) && value.type === 'connected')
      ) {
        retry('error');
        return;
      }
      const next = applySessionRecoveryEvent(recovery, value);
      if (next === recovery) return;
      const previous = recovery.status;
      recovery = next;
      handlers.onRecovery(recovery);
      if (!current()) return;
      if (recovery.status === 'deleted' || recovery.status === 'unsupported') {
        stop();
        handlers.onStatusChange(
          recovery.status === 'deleted' ? 'closed' : 'error',
        );
      } else if (recovery.status === 'resync') retry('error');
      else if (recovery.status === 'live' && previous !== 'live') {
        clearBootstrap();
        delay = INITIAL_DELAY_MS;
        handlers.onStatusChange('open');
      }
    };
    native.onerror = () => {
      if (current()) retry('error');
    };
  }
  window.addEventListener('offline', offline);
  window.addEventListener('online', reload);
  open();
  return { close: stop, reload };
}
