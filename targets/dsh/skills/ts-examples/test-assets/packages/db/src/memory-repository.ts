import { randomUUID } from 'node:crypto';
import { nextSessionRevision } from './session-revision.js';
import { isDeepStrictEqual } from 'node:util';
import type {
  RevisionedSessionSnapshot,
  CreateSessionInput,
  CreateSessionItemInput,
  SessionId,
  SessionItem,
  SessionItemId,
  SessionSnapshot,
  SessionSummary,
  UpdateSessionInput,
  UpdateSessionItemInput,
} from '@starter/types';
import type {
  ClaimedJob,
  JobEnqueueOptions,
  JobOwnership,
  JobRecurrenceOptions,
  JobRecord,
  JobRepository,
  SessionRepository,
  SessionMutation,
  SessionDeletion,
} from './repository.js';
import {
  validateJobLeaseDuration,
  validateJobMaxAttempts,
  snapshotJobPayload,
  assertOneOffPayload,
  recurringPayload,
  validateRecurrenceKey,
  validateRecurrenceInterval,
} from './job-policy.js';

/**
 * In-memory implementation of both ports.
 *
 * Not a toy: it is what the test suite runs against, and what a fresh checkout
 * with no `DATABASE_URL` boots with — so `pnpm dev` works before anyone has
 * installed Postgres. It maintains exactly the same invariants as the Postgres
 * implementation, which is what makes the shared test suite meaningful.
 */
interface StoredSession {
  id: SessionId;
  revision: number;
  name: string;
  status: 'idle' | 'active' | 'closed';
  items: SessionItem[];
  createdAt: string;
  updatedAt: string;
  lastReadAt: number;
}

export class InMemorySessionRepository implements SessionRepository {
  private readonly sessions = new Map<SessionId, StoredSession>();

  async create(
    input: CreateSessionInput,
  ): Promise<SessionMutation<SessionSnapshot>> {
    const now = new Date().toISOString();
    const session: StoredSession = {
      id: randomUUID(),
      revision: 1,
      name: input.name,
      status: 'idle',
      items: (input.items ?? []).map((item, index) => buildItem(item, index)),
      createdAt: now,
      updatedAt: now,
      lastReadAt: Date.now(),
    };
    this.sessions.set(session.id, session);
    return sessionResult(toSnapshot(session), session);
  }

  async findById(sessionId: SessionId): Promise<SessionSnapshot | null> {
    const session = this.sessions.get(sessionId);
    return session ? toSnapshot(session) : null;
  }

  async findRevisionedById(
    sessionId: SessionId,
  ): Promise<RevisionedSessionSnapshot | null> {
    const session = this.sessions.get(sessionId);
    return session
      ? { ...toSnapshot(session), revision: session.revision }
      : null;
  }

  async createIfBelowLimit(
    input: CreateSessionInput,
    hardLimit: number,
  ): Promise<SessionMutation<SessionSnapshot> | null> {
    // No await between the count and insertion: create mutates the map before
    // returning its promise, so competing admissions cannot share a free slot.
    if (this.sessions.size >= hardLimit) return null;
    return this.create(input);
  }

  async list(): Promise<SessionSummary[]> {
    return [...this.sessions.values()].sort(newestFirst).map(toSummary);
  }

  async count(): Promise<number> {
    return this.sessions.size;
  }

  async update(
    sessionId: SessionId,
    patch: UpdateSessionInput,
  ): Promise<SessionMutation<SessionSnapshot> | null> {
    const session = this.sessions.get(sessionId);
    if (!session) return null;

    const revision = nextSessionRevision(session.revision);
    // Only the keys actually present are applied — an absent key must never
    // reset the stored value.
    if (patch.name !== undefined) session.name = patch.name;
    if (patch.status !== undefined) session.status = patch.status;
    touch(session, revision);
    return sessionResult(toSnapshot(session), session);
  }

  async delete(sessionId: SessionId): Promise<SessionDeletion | null> {
    const session = this.sessions.get(sessionId);
    if (!session) return null;
    const deleted = deletionResult(session);
    this.sessions.delete(sessionId);
    return deleted;
  }

  async touch(sessionId: SessionId): Promise<void> {
    const session = this.sessions.get(sessionId);
    if (session) session.lastReadAt = Date.now();
  }

  async addItem(
    sessionId: SessionId,
    input: CreateSessionItemInput,
  ): Promise<SessionMutation<SessionItem> | null> {
    const session = this.sessions.get(sessionId);
    if (!session) return null;

    const revision = nextSessionRevision(session.revision);
    const item = buildItem(input, session.items.length);
    session.items.push(item);
    touch(session, revision);
    return sessionResult({ ...item }, session);
  }

  async updateItem(
    sessionId: SessionId,
    itemId: SessionItemId,
    patch: UpdateSessionItemInput,
  ): Promise<SessionMutation<SessionItem> | null> {
    const session = this.sessions.get(sessionId);
    if (!session) return null;

    const index = session.items.findIndex((item) => item.id === itemId);
    if (index === -1) return null;

    const revision = nextSessionRevision(session.revision);
    const current = session.items[index] as SessionItem;
    const next: SessionItem = {
      ...current,
      ...(patch.kind !== undefined ? { kind: patch.kind } : {}),
      ...(patch.label !== undefined ? { label: patch.label } : {}),
      ...(patch.value !== undefined ? { value: patch.value } : {}),
      ...(patch.done !== undefined ? { done: patch.done } : {}),
      updatedAt: new Date().toISOString(),
    };
    session.items[index] = next;

    if (patch.order !== undefined && patch.order !== current.order) {
      move(session.items, itemId, patch.order);
    }

    touch(session, revision);
    const moved = session.items.find(
      (item) => item.id === itemId,
    ) as SessionItem;
    return sessionResult({ ...moved }, session);
  }

  async removeItem(
    sessionId: SessionId,
    itemId: SessionItemId,
  ): Promise<SessionMutation<SessionItemId> | null> {
    const session = this.sessions.get(sessionId);
    if (!session || !session.items.some((item) => item.id === itemId))
      return null;
    const revision = nextSessionRevision(session.revision);
    session.items = reindex(session.items.filter((item) => item.id !== itemId));
    touch(session, revision);
    return sessionResult(itemId, session);
  }

  async deleteIdle(before: Date): Promise<SessionDeletion[]> {
    return this.deleteSelected(
      [...this.sessions.values()].filter(
        (session) => session.lastReadAt < before.getTime(),
      ),
    );
  }

  async deleteOverflow(
    keep: number,
    touchedBefore: Date,
  ): Promise<SessionDeletion[]> {
    const excess = [...this.sessions.values()]
      .sort(newestFirst)
      .slice(keep)
      .filter((session) => session.lastReadAt < touchedBefore.getTime());
    return this.deleteSelected(excess);
  }

  private deleteSelected(selected: StoredSession[]): SessionDeletion[] {
    // Validate the whole batch before any deletion, matching transaction rollback.
    const deleted = selected.map(deletionResult);
    for (const session of selected) this.sessions.delete(session.id);
    return deleted;
  }

  /** Test helper — drops everything. Not part of the port. */
  clear(): void {
    this.sessions.clear();
  }
}

type StoredJob = JobRecord & {
  runAt: number;
  lockedAt: number | null;
  completedAt: number | null;
  failedAt: number | null;
};

export class InMemoryJobRepository implements JobRepository {
  private readonly rows = new Map<string, StoredJob>();

  constructor(
    private readonly defaultMaxAttempts = 5,
    private readonly clock = () => new Date(),
  ) {
    validateJobMaxAttempts(defaultMaxAttempts);
  }

  private createRow(
    kind: string,
    payload: Record<string, unknown>,
    options: JobEnqueueOptions,
    recurrence?: { key: string; scheduledFor: Date },
  ): StoredJob {
    return {
      id: randomUUID(),
      kind,
      payload: snapshotJobPayload(payload),
      attempts: 0,
      maxAttempts: validateJobMaxAttempts(
        options.maxAttempts ?? this.defaultMaxAttempts,
      ),
      leaseExpiresAt: null,
      ownershipToken: null,
      recurrenceKey: recurrence?.key ?? null,
      recurrenceRunAt: recurrence ? new Date(recurrence.scheduledFor) : null,
      runAt: (options.runAt ?? this.clock()).getTime(),
      lockedAt: null,
      completedAt: null,
      failedAt: null,
    };
  }

  async enqueue(
    kind: string,
    payload: Record<string, unknown> = {},
    options: JobEnqueueOptions = {},
  ): Promise<string> {
    const persisted = snapshotJobPayload(payload);
    assertOneOffPayload(persisted);
    const row = this.createRow(kind, persisted, options);
    this.rows.set(row.id, row);
    return row.id;
  }

  async registerRecurring(
    kind: string,
    payload: Record<string, unknown>,
    options: JobRecurrenceOptions,
  ): Promise<string> {
    validateRecurrenceKey(options.key);
    const persisted = recurringPayload(payload, options.everyMs);
    const maxAttempts = validateJobMaxAttempts(
      options.maxAttempts ?? this.defaultMaxAttempts,
    );
    const history = [...this.rows.values()].filter(
      (row) => row.recurrenceKey === options.key,
    );
    if (
      history.some(
        (row) =>
          row.kind !== kind ||
          row.maxAttempts !== maxAttempts ||
          !row.recurrenceRunAt ||
          !isDeepStrictEqual(row.payload, persisted),
      )
    )
      throw new Error(
        'Recurring job configuration differs from its registered history.',
      );
    const first = history[0];
    if (first) return first.id;
    // No await between the history check and initial insertion.
    const scheduledFor = this.clock();
    const row = this.createRow(
      kind,
      persisted,
      { runAt: scheduledFor, maxAttempts },
      { key: options.key, scheduledFor },
    );
    this.rows.set(row.id, row);
    return row.id;
  }

  async abandonLegacyRecurring(): Promise<number> {
    let abandoned = 0;
    for (const row of this.rows.values()) {
      if (
        row.completedAt !== null ||
        row.failedAt !== null ||
        row.recurrenceKey !== null ||
        typeof row.payload.everyMs !== 'number' ||
        row.payload.everyMs <= 0
      )
        continue;
      this.clearOwnership(row);
      row.failedAt = this.clock().getTime();
      abandoned += 1;
    }
    return abandoned;
  }

  async claim(
    _workerId: string,
    limit: number,
    leaseMs: number,
  ): Promise<ClaimedJob[]> {
    validateJobLeaseDuration(leaseMs);
    validateJobMaxAttempts(limit);
    const now = this.clock().getTime();
    const pending = [...this.rows.values()].filter(
      (row) => row.completedAt === null && row.failedAt === null,
    );
    const expired = (row: StoredJob) =>
      row.lockedAt !== null &&
      row.ownershipToken !== null &&
      row.leaseExpiresAt !== null &&
      row.leaseExpiresAt.getTime() <= now;
    for (const row of pending
      .filter((row) => expired(row) && row.attempts >= row.maxAttempts)
      .sort(
        (a, b) =>
          (a.leaseExpiresAt?.getTime() ?? 0) -
            (b.leaseExpiresAt?.getTime() ?? 0) || a.id.localeCompare(b.id),
      )
      .slice(0, limit)) {
      row.failedAt = now;
      this.clearOwnership(row);
    }
    const claimable = pending
      .filter(
        (row) =>
          row.failedAt === null &&
          row.attempts < row.maxAttempts &&
          row.runAt <= now &&
          ((row.lockedAt === null &&
            row.ownershipToken === null &&
            row.leaseExpiresAt === null) ||
            expired(row)),
      )
      .sort((a, b) => a.runAt - b.runAt || a.id.localeCompare(b.id))
      .slice(0, limit);
    return claimable.map((row) => {
      const token = randomUUID();
      const deadline = new Date(now + leaseMs);
      row.lockedAt = now;
      row.attempts += 1;
      row.ownershipToken = token;
      row.leaseExpiresAt = deadline;
      return {
        id: row.id,
        kind: row.kind,
        payload: snapshotJobPayload(row.payload),
        attempts: row.attempts,
        maxAttempts: row.maxAttempts,
        ownershipToken: token,
        leaseExpiresAt: new Date(deadline),
        recurrenceKey: row.recurrenceKey,
        recurrenceRunAt: row.recurrenceRunAt
          ? new Date(row.recurrenceRunAt)
          : null,
      };
    });
  }

  private owned(ownership: JobOwnership): StoredJob | undefined {
    const row = this.rows.get(ownership.id);
    if (
      !row ||
      row.completedAt !== null ||
      row.failedAt !== null ||
      row.lockedAt === null ||
      row.ownershipToken !== ownership.token ||
      !row.leaseExpiresAt ||
      row.leaseExpiresAt.getTime() <= this.clock().getTime()
    )
      return undefined;
    return row;
  }

  private clearOwnership(row: StoredJob): void {
    row.lockedAt = null;
    row.ownershipToken = null;
    row.leaseExpiresAt = null;
  }

  async renew(ownership: JobOwnership, leaseMs: number): Promise<boolean> {
    validateJobLeaseDuration(leaseMs);
    const row = this.owned(ownership);
    if (!row) return false;
    row.leaseExpiresAt = new Date(this.clock().getTime() + leaseMs);
    return true;
  }

  async complete(ownership: JobOwnership): Promise<boolean> {
    const row = this.owned(ownership);
    if (!row) return false;
    const completedAt = this.clock().getTime();
    let successor: StoredJob | undefined;
    if (row.recurrenceKey !== null) {
      if (row.recurrenceRunAt === null)
        throw new Error('Invalid recurring job metadata.');
      const nextTime = new Date(
        completedAt + validateRecurrenceInterval(row.payload.everyMs),
      );
      successor = this.createRow(
        row.kind,
        row.payload,
        { runAt: nextTime, maxAttempts: row.maxAttempts },
        { key: row.recurrenceKey, scheduledFor: nextTime },
      );
    }
    // Prepare the successor before changing terminal state, then publish both
    // synchronously. Returned payload objects cannot mutate the stored row.
    row.completedAt = completedAt;
    this.clearOwnership(row);
    if (successor) this.rows.set(successor.id, successor);
    return true;
  }

  async fail(
    ownership: JobOwnership,
    _error: string,
    retryDelayMs: number,
  ): Promise<boolean> {
    const row = this.owned(ownership);
    if (!row) return false;
    this.clearOwnership(row);
    if (row.attempts >= row.maxAttempts) row.failedAt = this.clock().getTime();
    else row.runAt = this.clock().getTime() + retryDelayMs;
    return true;
  }

  async abandon(ownership: JobOwnership, _error: string): Promise<boolean> {
    const row = this.owned(ownership);
    if (!row) return false;
    this.clearOwnership(row);
    row.failedAt = this.clock().getTime();
    return true;
  }

  async prepareLegacyLeases(): Promise<{
    requeued: number;
    abandoned: number;
  }> {
    const pending = [...this.rows.values()].filter(
      (row) => row.completedAt === null && row.failedAt === null,
    );
    if (
      pending.some(
        (row) =>
          (row.ownershipToken === null) !== (row.leaseExpiresAt === null) ||
          (row.lockedAt === null &&
            (row.ownershipToken !== null || row.leaseExpiresAt !== null)),
      )
    )
      throw new Error(
        'Invalid job ownership metadata; worker startup stopped.',
      );
    let requeued = 0;
    let abandoned = 0;
    for (const row of pending) {
      if (
        row.lockedAt === null ||
        row.ownershipToken !== null ||
        row.leaseExpiresAt !== null
      )
        continue;
      this.clearOwnership(row);
      if (row.attempts >= row.maxAttempts) {
        row.failedAt = this.clock().getTime();
        abandoned += 1;
      } else requeued += 1;
    }
    return { requeued, abandoned };
  }

  async abandonPendingByKind(kind: string, _error: string): Promise<number> {
    let retired = 0;
    for (const row of this.rows.values()) {
      if (
        row.kind !== kind ||
        row.completedAt !== null ||
        row.failedAt !== null
      )
        continue;
      this.clearOwnership(row);
      row.failedAt = this.clock().getTime();
      retired += 1;
    }
    return retired;
  }

  async pendingCount(): Promise<number> {
    return [...this.rows.values()].filter(
      (row) => row.completedAt === null && row.failedAt === null,
    ).length;
  }

  clear(): void {
    this.rows.clear();
  }
}

// --- invariants shared with the Postgres implementation ---------------------

function sessionResult<T>(
  value: T,
  session: StoredSession,
): SessionMutation<T> {
  return { value, revision: session.revision, updatedAt: session.updatedAt };
}

function deletionResult(session: StoredSession): SessionDeletion {
  return {
    id: session.id,
    revision: nextSessionRevision(session.revision),
    updatedAt: new Date().toISOString(),
  };
}

function newestFirst(a: StoredSession, b: StoredSession): number {
  return (
    Date.parse(b.createdAt) - Date.parse(a.createdAt) ||
    b.id.localeCompare(a.id)
  );
}

function buildItem(input: CreateSessionItemInput, order: number): SessionItem {
  const now = new Date().toISOString();
  return {
    id: randomUUID(),
    kind: input.kind,
    label: input.label,
    value: input.value,
    order,
    done: false,
    createdAt: now,
    updatedAt: now,
  };
}

function touch(session: StoredSession, revision: number): void {
  session.revision = revision;
  session.updatedAt = new Date().toISOString();
  session.lastReadAt = Date.now();
}

/**
 * Renumber by array position. Separate from `reindex` on purpose: after a move
 * the array order IS the intent, so sorting by the stale `order` field first
 * would undo the move — which it did, until the contract test caught it.
 */
function assignOrder(items: SessionItem[]): SessionItem[] {
  return items.map((item, order) =>
    item.order === order ? item : { ...item, order },
  );
}

/** Keep `order` contiguous and 0-based after a removal, preserving the sequence. */
function reindex(items: SessionItem[]): SessionItem[] {
  return assignOrder([...items].sort((a, b) => a.order - b.order));
}

function move(
  items: SessionItem[],
  itemId: SessionItemId,
  target: number,
): void {
  const ordered = [...items].sort((a, b) => a.order - b.order);
  const from = ordered.findIndex((item) => item.id === itemId);
  if (from === -1) return;

  const to = Math.max(0, Math.min(target, ordered.length - 1));
  const [moved] = ordered.splice(from, 1);
  if (!moved) return;
  ordered.splice(to, 0, moved);

  items.length = 0;
  items.push(...assignOrder(ordered));
}

function toSnapshot(session: StoredSession): SessionSnapshot {
  return {
    id: session.id,
    name: session.name,
    status: session.status,
    items: session.items.map((item) => ({ ...item })),
    // Participants are a property of the live event bus, not of storage; the
    // service layer merges them in.
    participants: [],
    createdAt: session.createdAt,
    updatedAt: session.updatedAt,
  };
}

function toSummary(session: StoredSession): SessionSummary {
  return {
    id: session.id,
    name: session.name,
    status: session.status,
    itemCount: session.items.length,
    participantCount: 0,
    createdAt: session.createdAt,
    updatedAt: session.updatedAt,
  };
}
