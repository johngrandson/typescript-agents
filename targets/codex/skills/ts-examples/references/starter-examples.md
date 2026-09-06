# Verified starter excerpts

These excerpts retain their original imports and setup in the cited source files.
The captured starter bytes, including local changes, define the examples.
Each category has a source hash and an executed test suite in `starter-examples.json`.
The execution evidence lives in `docs/reference/example-verification.md`.
These excerpts are not standalone programs.

## Contract dto

Source: `packages/types/src/session.ts`.

Category: `contract-dto`. Verification: `types-contracts`.

```typescript
export type CreateSessionInput = Static<typeof CreateSessionSchema>;

/** Partial by design: only the fields actually sent are applied. */
```

## Contract envelope

Source: `packages/types/src/schemas/common.ts`.

Category: `response-envelope`. Verification: `types-contracts`.

```typescript
export const DetailOf = <T extends TSchema>(schema: T) =>
  ObjectType({ data: schema });

/** List totals retain the existing numeric wire contract. */
export const ListOf = <T extends TSchema>(schema: T) =>
  ObjectType({
    data: ArrayType(schema),
    total: Integer({ minimum: 0 }),
  });
```

## Route create

Source: `apps/api/src/modules/sessions/routes.ts`.

Category: `fastify-route`. Verification: `api-sessions`.

```typescript
    app.post(
      '/sessions',
      {
        schema: {
          summary: 'Create a session.',
          tags: ['sessions'],
          body: CreateSessionSchema,
          response: { 201: SessionDetailSchema, 429: ErrorResponseSchema },
        },
      },
      async (request, reply) =>
        reply.code(201).send({ data: await service.create(request.body) }),
    );
```

## Service update

Source: `apps/api/src/modules/sessions/service.ts`.

Category: `fastify-service`. Verification: `api-sessions`.

```typescript
  async update(
    sessionId: SessionId,
    patch: UpdateSessionInput,
  ): Promise<SessionSnapshot> {
    const result = await this.ctx.repositories.sessions.update(
      sessionId,
      patch,
    );
    if (!result) throw notFound(sessionId);

    const { value: snapshot, ...metadata } = result;
    const withParticipants = this.withParticipants(snapshot);
    this.ctx.bus.broadcast(sessionId, {
      ...metadata,
      type: 'session_updated',
      sessionId,
      session: withParticipants,
    });
    return withParticipants;
  }
```

## Job port

Source: `packages/db/src/repository.ts`.

Category: `job-ownership`. Verification: `memory-and-isolation`.

```typescript
export interface JobOwnership {
  id: string;
  token: string;
}

export interface ClaimedJob extends JobRecord {
  leaseExpiresAt: Date;
  ownershipToken: string;
}
```

## Job tick

Source: `apps/worker/src/runner.ts`.

Category: `job-sequencing`. Verification: `worker-retry-idempotency`.

```typescript
  tick(): Promise<TickResult> {
    if (this.stopped || this.active)
      return Promise.resolve({ processed: 0, failed: 0 });
    this.active = this.drainBatch().finally(() => {
      this.active = null;
    });
    return this.active;
  }
```

## Database error

Source: `packages/db/src/errors.ts`.

Category: `database-error`. Verification: `postgres-and-migrations`.

```typescript
export function databaseErrorMessage(error: unknown): string | undefined {
  if (!(error instanceof DrizzleQueryError)) return undefined;

  const cause = error.cause;
  const code = cause && 'code' in cause ? cause.code : undefined;
  return typeof code === 'string' &&
    code.length === 5 &&
    /^[0-9A-Z]{5}$/.test(code)
    ? `Database query failed (SQLSTATE ${code})`
    : 'Database query failed';
}
```

## Projection

Source: `packages/types/src/session-projection.ts`.

Category: `client-projection`. Verification: `types-contracts`.

```typescript
function dedupeParticipants(
  participants: SessionParticipant[],
): SessionParticipant[] {
  const seen = new Map<string, SessionParticipant>();
  for (const participant of participants) {
    seen.set(participant.clientId, participant);
  }
  return [...seen.values()];
}
```

## Server action

Source: `apps/web/app/actions/actions.ts`.

Category: `server-action`. Verification: `web-server-actions`.

```typescript
export async function updateSession(
  sessionId: SessionId,
  input: UpdateSessionInput,
): Promise<ActionResult<SessionSnapshot>> {
  return runMutation(
    () => client().updateSession(sessionId, input),
    `/sessions/${sessionId}`,
  );
}
```

## Mobile port

Source: `apps/mobile/src/services/apiService.ts`.

Category: `mobile-port`. Verification: `mobile-service`.

```typescript
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
```

## Narrow storage error

Source: `apps/worker/src/handlers/archive-session.ts`.

Category: `narrow-storage-error`. Verification: `worker-retry-idempotency`.

```typescript
      async function alreadyPublished(): Promise<boolean> {
        ctx.signal.throwIfAborted();
        try {
          await store.read(fileName);
          ctx.signal.throwIfAborted();
          return true;
        } catch (error) {
          ctx.signal.throwIfAborted();
          if (error instanceof DocumentStoreError) {
            if (error.kind === 'not-found') return false;
            if (error.kind === 'invalid-document')
              throw new PermanentJobError(
                'Existing archive is invalid; operator repair is required.',
              );
          }
          throw error;
        }
      }
```

## Inject test

Source: `apps/api/src/modules/sessions/__tests__/routes.test.ts`.

Category: `inject-test`. Verification: `api-sessions`.

```typescript
  it('rejects an invalid body with the canonical error envelope', async () => {
    const response = await app.inject({
      method: 'POST',
      url: '/sessions',
      payload: { name: '' },
    });

    expect(response.statusCode).toBe(400);
    expect(response.json()).toEqual({
      error: { code: 'VALIDATION_FAILED', message: expect.any(String) },
    });
  });
```

## TypeBox input schema

Source: `packages/types/src/schemas/session.ts`.

Category: `typebox-contract`. Verification: `types-contracts`.

The schema rejects additional fields and bounds the session name and item list.

```typescript
export const CreateSessionSchema = ObjectType(
  {
    name: StringType({ minLength: 1, maxLength: 200 }),
    items: Optional(ArrayType(CreateSessionItemSchema, { maxItems: 500 })),
  },
  { additionalProperties: false },
);
```

## Memory repository

Source: `packages/db/src/memory-repository.ts`.

Category: `repository-memory`. Verification: `memory-and-isolation`.

The memory implementation creates revision one and returns the same mutation contract used by PostgreSQL.

```typescript
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
```

## PostgreSQL repository

Source: `packages/db/src/drizzle-repository.ts`.

Category: `repository-postgres`. Verification: `postgres-and-migrations`.

A single statement reads the session, children and revision from one MVCC snapshot.

```typescript
  private async readSnapshot(sessionId: SessionId) {
    // Session fields, children and revision come from one MVCC statement snapshot.
    const rows = await this.db
      .select({ session: sessions, item: sessionItems })
      .from(sessions)
      .leftJoin(sessionItems, eq(sessionItems.sessionId, sessions.id))
      .where(eq(sessions.id, sessionId));
    const first = rows[0];
    return first
      ? {
          session: first.session,
          items: rows.flatMap(({ item }) => (item ? [item] : [])),
        }
      : null;
  }
```

## Session revision migration

Source: `packages/db/drizzle/0004_session_revisions.sql`.

Category: `schema-migration`. Verification: `postgres-and-migrations`.

The existing migration adds bounded revisions. The real PostgreSQL upgrade test preserves existing data and migration history when this
migration runs again.

```sql
ALTER TABLE "sessions" ADD COLUMN "revision" bigint DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE "sessions" ADD CONSTRAINT "sessions_revision_check" CHECK ("sessions"."revision" between 0 and 9007199254740991);
```

## SSE proxy

Source: `apps/web/app/api/sessions/[sessionId]/events/route.ts`.

Category: `sse-proxy`. Verification: `web-sse-recovery`.

The proxy forwards the negotiated protocol and caller cancellation to the upstream stream.

```typescript
  const protocol = request.nextUrl.searchParams.getAll('protocol');
  const query = new URLSearchParams();
  for (const value of protocol) query.append('protocol', value);
  const streamUrl = `${baseUrl}/sessions/${encodeURIComponent(sessionId)}/events${query.size ? `?${query}` : ''}`;
  const deadline = createRequestDeadline(10_000, request.signal);
  try {
    deadline.signal.throwIfAborted();
    const upstream = await fetch(streamUrl, {
      headers: { Accept: 'text/event-stream' },
      signal: deadline.signal,
      cache: 'no-store',
    });
```

## SSE recovery update

Source: `apps/web/lib/session-stream.ts`.

Category: `sse-update`. Verification: `web-sse-recovery`.

Validated events advance the shared recovery state. Deleted, unsupported and resync states determine stream closure or retry.

```typescript
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
```

## Mobile store

Source: `apps/mobile/src/store/sessionsStore.ts`.

Category: `mobile-store`. Verification: `mobile-store-and-hook`.

Only the current owner can apply a recovery snapshot. The store also updates the list summary and removes deleted sessions.

```typescript
  setRecovery: (owner, recovery) =>
    set((state) => {
      if (state.activeOwner !== owner) return state;
      if (recovery.status === 'deleted')
        return {
          active: null,
          summaries: state.summaries.filter(
            (row) => row.id !== recovery.sessionId,
          ),
        };
      if (recovery.status === 'unsupported') return { active: null };
      if (!recovery.snapshot || recovery.snapshot === state.active)
        return state;
      return {
        active: recovery.snapshot,
        summaries: syncSummary(state.summaries, recovery.snapshot),
      };
    }),
```

## Mobile hook ownership

Source: `apps/mobile/src/screens/SessionDetail/useSessionDetail.ts`.

Category: `mobile-hook`. Verification: `mobile-store-and-hook`.

The API origin and session identity determine ownership. A previous mounted screen cannot overwrite the active selection.

```typescript
  const connection = useMemo(
    () => ({ api, apiUrl, sessionId, token: Symbol(sessionId) }),
    [api, apiUrl, sessionId],
  );
  const session = useSessionsStore((state) =>
    state.activeOwner === connection.token ? state.active : null,
  );
```

## Mobile service update

Source: `apps/mobile/src/services/apiService.ts`.

Category: `mobile-service`. Verification: `mobile-service`.

The service sends a PATCH through the shared request function and validates the returned session snapshot.

```typescript
    updateSession: (sessionId, input) =>
      data(`/sessions/${sessionId}`, isSessionSnapshot, {
        method: 'PATCH',
        body: input,
      }),
```

## Job retry

Source: `apps/worker/src/runner.ts`.

Category: `job-retry`. Verification: `worker-retry-idempotency`.

Transient failures use bounded exponential backoff. Permanent failures abandon the owned job; exhausted attempts are recorded separately.

```typescript
          const backoff = this.backoffFor(job.attempts);
          const permanent = failure instanceof PermanentJobError;
          const retrying = !permanent && job.attempts < job.maxAttempts;
          this.log.warn('job failed', {
            kind: job.kind,
            id: job.id,
            attempt: job.attempts,
            maxAttempts: job.maxAttempts,
            disposition: permanent
              ? 'abandoned'
              : retrying
                ? 'retry'
                : 'exhausted',
            ...(retrying ? { retryInMs: backoff } : {}),
            error: databaseErrorMessage(failure) ?? failure,
          });
          await this.acknowledge(permanent ? 'abandon' : 'fail', () =>
            permanent
              ? this.repositories.jobs.abandon(ownership, message)
              : this.repositories.jobs.fail(ownership, message, backoff),
          );
```

## Job idempotency

Source: `apps/worker/src/handlers/archive-session.ts`.

Category: `job-idempotency`. Verification: `worker-retry-idempotency`.

The archive key includes the session and job identities. A verified existing archive makes a repeated delivery return before publishing
another file.

```typescript
      if (await alreadyPublished()) {
        ctx.log.info('archive already published', {
          sessionId,
          jobId,
          fileName,
        });
        return;
      }
```
