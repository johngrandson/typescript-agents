'use server';

import { runMutation } from '@/lib/action-result.server';
import { createStarterApiClient } from '@/lib/api-client';
import { getServerSideApiUrl } from '@/lib/server-url.server';
import type {
  ActionResult,
  CreateSessionInput,
  CreateSessionItemInput,
  SessionId,
  SessionItem,
  SessionItemId,
  SessionSnapshot,
  UpdateSessionInput,
  UpdateSessionItemInput,
} from '@/lib/types';

/**
 * The single funnel for every mutation the UI performs.
 *
 * No component calls `fetch` and no component builds a URL. That is what makes
 * "where does this request come from?" answerable by grepping one file, and it
 * keeps the API base URL server-side.
 *
 * Note: never `export type { … }` from a `'use server'` module — the bundler
 * rejects it. Consumers import types from `@/lib/types` instead.
 */

function client() {
  return createStarterApiClient(getServerSideApiUrl());
}

export async function createSession(
  input: CreateSessionInput,
): Promise<ActionResult<SessionSnapshot>> {
  return runMutation(() => client().createSession(input), '/');
}

export async function updateSession(
  sessionId: SessionId,
  input: UpdateSessionInput,
): Promise<ActionResult<SessionSnapshot>> {
  return runMutation(
    () => client().updateSession(sessionId, input),
    `/sessions/${sessionId}`,
  );
}

export async function deleteSession(
  sessionId: SessionId,
): Promise<ActionResult<null>> {
  return runMutation(async () => {
    await client().deleteSession(sessionId);
    return null;
  }, '/');
}

export async function addItem(
  sessionId: SessionId,
  input: CreateSessionItemInput,
): Promise<ActionResult<SessionItem>> {
  return runMutation(
    () => client().addItem(sessionId, input),
    `/sessions/${sessionId}`,
  );
}

/**
 * Partial update: only the fields the caller actually changed are sent.
 * Passing `undefined` for untouched fields would overwrite them server-side on
 * any endpoint that does not treat `undefined` as "absent".
 */
export async function updateItem(
  sessionId: SessionId,
  itemId: SessionItemId,
  input: UpdateSessionItemInput,
): Promise<ActionResult<SessionItem>> {
  return runMutation(
    () => client().updateItem(sessionId, itemId, input),
    `/sessions/${sessionId}`,
  );
}

export async function removeItem(
  sessionId: SessionId,
  itemId: SessionItemId,
): Promise<ActionResult<null>> {
  return runMutation(async () => {
    await client().removeItem(sessionId, itemId);
    return null;
  }, `/sessions/${sessionId}`);
}
