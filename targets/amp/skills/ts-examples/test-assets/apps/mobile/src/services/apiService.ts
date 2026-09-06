import type {
  CreateSessionInput,
  CreateSessionItemInput,
  SessionId,
  SessionItem,
  SessionItemId,
  SessionSnapshot,
  SessionSummary,
  UpdateSessionInput,
  UpdateSessionItemInput,
} from '../types';
import {
  isDataResponse,
  isErrorResponse,
  isListResponse,
  isSessionItem,
  isSessionSnapshot,
  isSessionSummary,
  registerContractFormats,
} from '../types/validators';

/**
 * REST transport for the mobile app.
 *
 * Mirrors the web client's shape (interface + factory + one request funnel) but
 * stays a separate implementation: React Native's fetch has different timeout
 * and abort behaviour, and the base URL comes from app config, not env vars
 * baked at build time.
 */

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

export interface ApiService {
  listSessions(): Promise<SessionSummary[]>;
  getSession(sessionId: SessionId): Promise<SessionSnapshot>;
  createSession(input: CreateSessionInput): Promise<SessionSnapshot>;
  updateSession(
    sessionId: SessionId,
    input: UpdateSessionInput,
  ): Promise<SessionSnapshot>;
  addItem(
    sessionId: SessionId,
    input: CreateSessionItemInput,
  ): Promise<SessionItem>;
  updateItem(
    sessionId: SessionId,
    itemId: SessionItemId,
    input: UpdateSessionItemInput,
  ): Promise<SessionItem>;
  removeItem(sessionId: SessionId, itemId: SessionItemId): Promise<void>;
}

const DEFAULT_TIMEOUT_MS = 10_000;

export async function request<T>(
  baseUrl: string,
  path: string,
  options: {
    method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
    body?: unknown;
    timeoutMs?: number;
  } = {},
): Promise<T> {
  const { method = 'GET', body, timeoutMs = DEFAULT_TIMEOUT_MS } = options;

  // A phone on a flaky network will hang forever without an explicit timeout;
  // there is no browser tab for the user to close.
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${baseUrl}${path}`, {
      method,
      signal: controller.signal,
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });

    if (response.status === 204) return undefined as T;

    const payload: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      // Canonical failure envelope: `{ error: { code, message } }`.
      const failure = isErrorResponse(payload) ? payload.error : null;
      throw new ApiError(
        response.status,
        failure?.code ?? 'UNKNOWN_ERROR',
        failure?.message ?? `Request failed with ${response.status}.`,
      );
    }

    return payload as T;
  } catch (cause) {
    if (cause instanceof ApiError) throw cause;
    if (cause instanceof Error && cause.name === 'AbortError') {
      throw new ApiError(408, 'REQUEST_TIMEOUT', `${path} timed out.`);
    }
    throw new ApiError(503, 'API_UNREACHABLE', `Could not reach ${baseUrl}.`);
  } finally {
    clearTimeout(timer);
  }
}

export function createApiService(baseUrl: string): ApiService {
  registerContractFormats();
  const normalized = baseUrl.replace(/\/+$/, '');
  const send = <T>(path: string, options?: Parameters<typeof request>[2]) =>
    request<T>(normalized, path, options);
  const data = async <T>(
    path: string,
    accepts: (value: unknown) => value is T,
    options?: Parameters<typeof request>[2],
  ): Promise<T> => {
    const payload = await send<unknown>(path, options);
    if (!isDataResponse(payload) || !accepts(payload.data))
      throw new ApiError(
        502,
        'API_INVALID_RESPONSE',
        'The API returned an invalid response.',
      );
    return payload.data;
  };

  return {
    async listSessions() {
      const payload = await send<unknown>('/sessions');
      if (!isListResponse(payload) || !payload.data.every(isSessionSummary))
        throw new ApiError(
          502,
          'API_INVALID_RESPONSE',
          'The API returned an invalid response.',
        );
      return payload.data;
    },
    getSession: (sessionId) =>
      data(`/sessions/${sessionId}`, isSessionSnapshot),
    createSession: (input) =>
      data('/sessions', isSessionSnapshot, { method: 'POST', body: input }),
    updateSession: (sessionId, input) =>
      data(`/sessions/${sessionId}`, isSessionSnapshot, {
        method: 'PATCH',
        body: input,
      }),
    addItem: (sessionId, input) =>
      data(`/sessions/${sessionId}/items`, isSessionItem, {
        method: 'POST',
        body: input,
      }),
    updateItem: (sessionId, itemId, input) =>
      data(`/sessions/${sessionId}/items/${itemId}`, isSessionItem, {
        method: 'PATCH',
        body: input,
      }),
    removeItem: (sessionId, itemId) =>
      send<void>(`/sessions/${sessionId}/items/${itemId}`, {
        method: 'DELETE',
      }),
  };
}
