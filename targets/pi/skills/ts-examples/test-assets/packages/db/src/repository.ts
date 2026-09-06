import type {
  RevisionedSessionSnapshot,
  SessionRevisionMetadata,
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

/**
 * What the domain needs from storage — and nothing more.
 *
 * Declaring the port as an interface is what lets the API run against Postgres
 * in production and against an in-memory implementation in tests and in a
 * `DATABASE_URL`-less checkout. The service never learns which one it got.
 *
 * Every method that returns a snapshot returns the *whole* snapshot: partial
 * returns push the job of re-assembling state onto every caller, and they
 * assemble it slightly differently.
 */
/** Result captured inside the same transaction as the successful write. */
export interface SessionMutation<T> extends SessionRevisionMetadata {
  value: T;
}

export interface SessionDeletion extends SessionRevisionMetadata {
  id: SessionId;
}

export interface SessionRepository {
  /** Unconditional creation for seed/import operations; admission uses the method below. */
  create(input: CreateSessionInput): Promise<SessionMutation<SessionSnapshot>>;
  /** Atomically count and create; null means the positive hard limit is reached. */
  createIfBelowLimit(
    input: CreateSessionInput,
    hardLimit: number,
  ): Promise<SessionMutation<SessionSnapshot> | null>;
  findById(sessionId: SessionId): Promise<SessionSnapshot | null>;
  findRevisionedById(
    sessionId: SessionId,
  ): Promise<RevisionedSessionSnapshot | null>;
  list(): Promise<SessionSummary[]>;
  count(): Promise<number>;
  update(
    sessionId: SessionId,
    patch: UpdateSessionInput,
  ): Promise<SessionMutation<SessionSnapshot> | null>;
  delete(sessionId: SessionId): Promise<SessionDeletion | null>;
  /** Mark the session as read, so the idle reaper leaves it alone. */
  touch(sessionId: SessionId): Promise<void>;

  addItem(
    sessionId: SessionId,
    input: CreateSessionItemInput,
  ): Promise<SessionMutation<SessionItem> | null>;
  updateItem(
    sessionId: SessionId,
    itemId: SessionItemId,
    patch: UpdateSessionItemInput,
  ): Promise<SessionMutation<SessionItem> | null>;
  removeItem(
    sessionId: SessionId,
    itemId: SessionItemId,
  ): Promise<SessionMutation<SessionItemId> | null>;

  /** Atomically delete sessions last touched strictly before the cutoff. */
  deleteIdle(before: Date): Promise<SessionDeletion[]>;
  /**
   * Keep the newest `keep` by createdAt/id. Atomically recheck the excess and
   * exclude sessions touched at or after `touchedBefore`. Return metadata from rows actually deleted.
   */
  deleteOverflow(keep: number, touchedBefore: Date): Promise<SessionDeletion[]>;
}

export interface JobRecord {
  id: string;
  kind: string;
  payload: Record<string, unknown>;
  attempts: number;
  maxAttempts: number;
  /** Null while unowned; every successful claim returns a current token and deadline. */
  leaseExpiresAt: Date | null;
  ownershipToken: string | null;
  /** Nullable for ordinary jobs and legacy payload-only recurring jobs. */
  recurrenceKey: string | null;
  recurrenceRunAt: Date | null;
}

export interface JobOwnership {
  id: string;
  token: string;
}

export interface ClaimedJob extends JobRecord {
  leaseExpiresAt: Date;
  ownershipToken: string;
}

export interface JobEnqueueOptions {
  runAt?: Date;
  maxAttempts?: number;
}

export interface JobRecurrenceOptions {
  /** Stable identity retained in history across process restarts. */
  key: string;
  everyMs: number;
  maxAttempts?: number;
}

/**
 * The worker's view of the jobs table. `claim` must be atomic across workers —
 * the Postgres implementation uses `FOR UPDATE SKIP LOCKED`.
 */
export interface JobRepository {
  enqueue(
    kind: string,
    payload?: Record<string, unknown>,
    options?: JobEnqueueOptions,
  ): Promise<string>;
  /** Register once; a terminal history never revives. Changed configuration fails. */
  registerRecurring(
    kind: string,
    payload: Record<string, unknown>,
    options: JobRecurrenceOptions,
  ): Promise<string>;
  /** Deployment transition after all payload-only scheduling workers stop. */
  abandonLegacyRecurring(): Promise<number>;
  claim(
    workerId: string,
    limit: number,
    leaseMs: number,
  ): Promise<ClaimedJob[]>;
  /** Extend only the current unexpired ownership; never revive an expired lease. */
  renew(ownership: JobOwnership, leaseMs: number): Promise<boolean>;
  complete(ownership: JobOwnership): Promise<boolean>;
  /** Reschedule with backoff, or mark failed once `maxAttempts` is spent. */
  fail(
    ownership: JobOwnership,
    error: string,
    retryDelayMs: number,
  ): Promise<boolean>;
  /**
   * Fail permanently, ignoring the remaining attempts. For errors that retrying
   * cannot fix — an unknown job kind, a malformed payload. `fail(..., 0)` is
   * *not* this: it reschedules immediately, which spins.
   */
  abandon(ownership: JobOwnership, error: string): Promise<boolean>;
  /** Deployment transition after every ID-only worker and transaction has stopped. */
  prepareLegacyLeases(): Promise<{ requeued: number; abandoned: number }>;
  /** Retire pending jobs of one kind, including future and already-claimed rows. */
  abandonPendingByKind(kind: string, error: string): Promise<number>;
  pendingCount(): Promise<number>;
}
