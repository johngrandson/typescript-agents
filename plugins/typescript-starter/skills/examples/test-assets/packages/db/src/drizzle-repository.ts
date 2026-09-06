import { and, desc, eq, inArray, lt, sql, type SQL } from 'drizzle-orm';
import type {
  RevisionedSessionSnapshot,
  SessionRevisionMetadata,
  CreateSessionInput,
  CreateSessionItemInput,
  SessionId,
  SessionItem,
  SessionItemId,
  SessionSnapshot,
  SessionStatus,
  SessionSummary,
  UpdateSessionInput,
  UpdateSessionItemInput,
} from '@starter/types';
import type { Database } from './client.js';
import type {
  SessionDeletion,
  SessionMutation,
  SessionRepository,
} from './repository.js';
import { nextSessionRevision } from './session-revision.js';
import {
  sessionItems,
  sessions,
  type SessionItemRow,
  type SessionRow,
} from './schema.js';

// Preserve existing direct imports while the job implementation grows separately.
export { DrizzleJobRepository } from './drizzle-job-repository.js';

/**
 * Postgres implementation of the session port.
 *
 * Multi-statement operations run inside a transaction — an add that appends the
 * row but fails before bumping `updated_at` leaves the session looking stale to
 * every client polling on it.
 */
export class DrizzleSessionRepository implements SessionRepository {
  constructor(private readonly db: Database) {}

  async create(
    input: CreateSessionInput,
  ): Promise<SessionMutation<SessionSnapshot>> {
    return this.db.transaction((tx) => insertSession(tx, input));
  }

  async createIfBelowLimit(
    input: CreateSessionInput,
    hardLimit: number,
  ): Promise<SessionMutation<SessionSnapshot> | null> {
    return this.db.transaction(
      async (tx) => {
        // Database-wide protocol shared by every API process: ASCII STAR is the
        // namespace; key 1 is session admission. The lock ends on commit/rollback.
        await tx.execute(sql`select pg_advisory_xact_lock(${0x53544152}, 1)`);
        // Keep this a later statement: after waiting, Read Committed sees the
        // preceding admission's commit rather than the lock statement's snapshot.
        const [row] = await tx
          .select({ total: sql<number>`count(*)::int` })
          .from(sessions);
        if (Number(row?.total ?? 0) >= hardLimit) return null;
        return insertSession(tx, input);
      },
      { isolationLevel: 'read committed' },
    );
  }

  async findById(sessionId: SessionId): Promise<SessionSnapshot | null> {
    const row = await this.readSnapshot(sessionId);
    return row ? toSnapshot(row.session, row.items) : null;
  }

  async findRevisionedById(
    sessionId: SessionId,
  ): Promise<RevisionedSessionSnapshot | null> {
    const row = await this.readSnapshot(sessionId);
    return row
      ? {
          ...toSnapshot(row.session, row.items),
          revision: row.session.revision,
        }
      : null;
  }

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

  async list(): Promise<SessionSummary[]> {
    // One aggregate query rather than N+1 counts — the list page asks for this
    // on every load.
    const rows = await this.db
      .select({
        id: sessions.id,
        name: sessions.name,
        status: sessions.status,
        createdAt: sessions.createdAt,
        updatedAt: sessions.updatedAt,
        itemCount: sql<number>`count(${sessionItems.id})::int`,
      })
      .from(sessions)
      .leftJoin(sessionItems, eq(sessionItems.sessionId, sessions.id))
      .groupBy(sessions.id)
      .orderBy(desc(sessions.createdAt), desc(sessions.id));

    return rows.map((row) => ({
      id: row.id,
      name: row.name,
      status: row.status as SessionStatus,
      itemCount: Number(row.itemCount),
      participantCount: 0,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    }));
  }

  async count(): Promise<number> {
    const [row] = await this.db
      .select({ total: sql<number>`count(*)::int` })
      .from(sessions);
    return Number(row?.total ?? 0);
  }

  async update(
    sessionId: SessionId,
    patch: UpdateSessionInput,
  ): Promise<SessionMutation<SessionSnapshot> | null> {
    // Spread only the present keys: an explicit `undefined` in a Drizzle `set`
    // is ignored, but building the object this way keeps that non-obvious
    // behaviour from being load-bearing.
    const values = {
      ...(patch.name !== undefined ? { name: patch.name } : {}),
      ...(patch.status !== undefined ? { status: patch.status } : {}),
      revision: sql`${sessions.revision} + 1`,
      updatedAt: sql`clock_timestamp()`,
      lastReadAt: sql`clock_timestamp()`,
    };

    return this.db.transaction(async (tx) => {
      // UPDATE holds the same parent lock used by item writers. Read the
      // result before commit so a later mutation cannot replace this response.
      const [row] = await tx
        .update(sessions)
        .set(values)
        .where(eq(sessions.id, sessionId))
        .returning();
      if (!row) return null;

      const items = await tx
        .select()
        .from(sessionItems)
        .where(eq(sessionItems.sessionId, sessionId));
      return sessionResult(toSnapshot(row, items), row);
    });
  }

  async delete(sessionId: SessionId): Promise<SessionDeletion | null> {
    const [deleted] = await this.deleteWhere(eq(sessions.id, sessionId));
    return deleted ?? null;
  }

  async touch(sessionId: SessionId): Promise<void> {
    await this.db
      .update(sessions)
      .set({ lastReadAt: new Date() })
      .where(eq(sessions.id, sessionId));
  }

  async addItem(
    sessionId: SessionId,
    input: CreateSessionItemInput,
  ): Promise<SessionMutation<SessionItem> | null> {
    return this.db.transaction(async (tx) => {
      if (!(await lockSession(tx, sessionId))) return null;

      const [{ next } = { next: 0 }] = await tx
        .select({
          next: sql<number>`coalesce(max(${sessionItems.sortOrder}) + 1, 0)::int`,
        })
        .from(sessionItems)
        .where(eq(sessionItems.sessionId, sessionId));

      const [row] = await tx
        .insert(sessionItems)
        .values({
          sessionId,
          kind: input.kind,
          label: input.label,
          value: input.value,
          sortOrder: Number(next),
        })
        .returning();
      if (!row) return null;

      const metadata = await bumpSession(tx, sessionId);
      return { value: toItem(row), ...metadata };
    });
  }

  async updateItem(
    sessionId: SessionId,
    itemId: SessionItemId,
    patch: UpdateSessionItemInput,
  ): Promise<SessionMutation<SessionItem> | null> {
    return this.db.transaction(async (tx) => {
      if (!(await lockSession(tx, sessionId))) return null;

      const [current] = await tx
        .select()
        .from(sessionItems)
        .where(
          and(
            eq(sessionItems.id, itemId),
            eq(sessionItems.sessionId, sessionId),
          ),
        );
      if (!current) return null;

      const [updated] = await tx
        .update(sessionItems)
        .set({
          ...(patch.kind !== undefined ? { kind: patch.kind } : {}),
          ...(patch.label !== undefined ? { label: patch.label } : {}),
          ...(patch.value !== undefined ? { value: patch.value } : {}),
          ...(patch.done !== undefined ? { done: patch.done } : {}),
          updatedAt: new Date(),
        })
        .where(eq(sessionItems.id, itemId))
        .returning();
      if (!updated) return null;

      if (patch.order !== undefined && patch.order !== current.sortOrder) {
        await reorder(tx, sessionId, itemId, patch.order);
      }
      const metadata = await bumpSession(tx, sessionId);

      const [final] = await tx
        .select()
        .from(sessionItems)
        .where(eq(sessionItems.id, itemId));
      if (!final) throw new Error('Updated item disappeared before commit.');
      return { value: toItem(final), ...metadata };
    });
  }

  async removeItem(
    sessionId: SessionId,
    itemId: SessionItemId,
  ): Promise<SessionMutation<SessionItemId> | null> {
    return this.db.transaction(async (tx) => {
      if (!(await lockSession(tx, sessionId))) return null;
      const deleted = await tx
        .delete(sessionItems)
        .where(
          and(
            eq(sessionItems.id, itemId),
            eq(sessionItems.sessionId, sessionId),
          ),
        )
        .returning({ id: sessionItems.id });
      if (deleted.length === 0) return null;
      await compact(tx, sessionId);
      const metadata = await bumpSession(tx, sessionId);
      return { value: itemId, ...metadata };
    });
  }

  async deleteIdle(before: Date): Promise<SessionDeletion[]> {
    return this.deleteWhere(lt(sessions.lastReadAt, before));
  }

  async deleteOverflow(
    keep: number,
    touchedBefore: Date,
  ): Promise<SessionDeletion[]> {
    const excess = this.db
      .select({ id: sessions.id })
      .from(sessions)
      .orderBy(desc(sessions.createdAt), desc(sessions.id))
      .offset(keep);
    // The direct touch predicate is rechecked after a concurrent parent update.
    return this.deleteWhere(
      sql`${inArray(sessions.id, excess)} and ${lt(sessions.lastReadAt, touchedBefore)}`,
    );
  }

  private async deleteWhere(condition: SQL): Promise<SessionDeletion[]> {
    return this.db.transaction(async (tx) => {
      const rows = await tx
        .delete(sessions)
        .where(condition)
        .returning({
          id: sessions.id,
          revision: sessions.revision,
          deletedAt: sql`clock_timestamp()`.mapWith(sessions.updatedAt),
        });
      // Validate before transaction completion: overflow rolls back every deletion.
      return rows.map((row) => ({
        id: row.id,
        revision: nextSessionRevision(row.revision),
        updatedAt: row.deletedAt.toISOString(),
      }));
    });
  }
}

// --- helpers ---------------------------------------------------------------

type Tx = Parameters<Parameters<Database['transaction']>[0]>[0];

async function insertSession(
  tx: Tx,
  input: CreateSessionInput,
): Promise<SessionMutation<SessionSnapshot>> {
  const [row] = await tx
    .insert(sessions)
    .values({ name: input.name, revision: 1 })
    .returning();
  if (!row) throw new Error('Insert returned no row.');
  const seeds = input.items ?? [];
  const items = seeds.length
    ? await tx
        .insert(sessionItems)
        .values(
          seeds.map((item, index) => ({
            sessionId: row.id,
            kind: item.kind,
            label: item.label,
            value: item.value,
            sortOrder: index,
          })),
        )
        .returning()
    : [];
  return sessionResult(toSnapshot(row, items), row);
}

/** All child writers acquire the parent first, matching UPDATE/DELETE order. */
async function lockSession(tx: Tx, sessionId: SessionId): Promise<boolean> {
  const [row] = await tx
    .select({ id: sessions.id })
    .from(sessions)
    .where(eq(sessions.id, sessionId))
    .for('update');
  return row !== undefined;
}

async function bumpSession(
  tx: Tx,
  sessionId: SessionId,
): Promise<SessionRevisionMetadata> {
  const [row] = await tx
    .update(sessions)
    .set({
      revision: sql`${sessions.revision} + 1`,
      updatedAt: sql`clock_timestamp()`,
      lastReadAt: sql`clock_timestamp()`,
    })
    .where(eq(sessions.id, sessionId))
    .returning({ revision: sessions.revision, updatedAt: sessions.updatedAt });
  if (!row) throw new Error('Locked session disappeared before commit.');
  return { revision: row.revision, updatedAt: row.updatedAt.toISOString() };
}

function sessionResult<T>(value: T, row: SessionRow): SessionMutation<T> {
  return {
    value,
    revision: row.revision,
    updatedAt: row.updatedAt.toISOString(),
  };
}

/**
 * Rewrite `sort_order` so it is contiguous and 0-based, preserving the current
 * sequence. `exceptId` is left untouched — during a move the parked row must
 * not be renumbered back into the pack, which is precisely the bug the shared
 * contract test caught between this implementation and the in-memory one.
 */
async function compact(
  tx: Tx,
  sessionId: SessionId,
  exceptId?: SessionItemId,
): Promise<void> {
  const excluded = exceptId ? sql`and id <> ${exceptId}` : sql``;

  await tx.execute(sql`
    update ${sessionItems} as target
       set sort_order = ranked.position
      from (
        select id, (row_number() over (order by sort_order) - 1)::int as position
          from ${sessionItems}
         where session_id = ${sessionId}
         ${excluded}
      ) as ranked
     where target.id = ranked.id
       and target.sort_order is distinct from ranked.position
  `);
}

async function reorder(
  tx: Tx,
  sessionId: SessionId,
  itemId: SessionItemId,
  target: number,
): Promise<void> {
  // Park the moved row below the range so it cannot collide, close the gap it
  // left behind (without renumbering it), open a slot at the destination, drop
  // it in, then normalise. One UPDATE cannot express this without passing
  // through a state that violates the ordering.
  await tx
    .update(sessionItems)
    .set({ sortOrder: -1 })
    .where(eq(sessionItems.id, itemId));
  await compact(tx, sessionId, itemId);

  await tx.execute(sql`
    update ${sessionItems}
       set sort_order = sort_order + 1
     where session_id = ${sessionId}
       and sort_order >= ${target}
       and id <> ${itemId}
  `);
  await tx
    .update(sessionItems)
    .set({ sortOrder: target })
    .where(eq(sessionItems.id, itemId));
  // A target past the end lands high; this pulls the whole list back to 0..n-1.
  await compact(tx, sessionId);
}

function toItem(row: SessionItemRow): SessionItem {
  return {
    id: row.id,
    kind: row.kind,
    label: row.label,
    value: row.value,
    order: row.sortOrder,
    done: row.done,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function toSnapshot(row: SessionRow, items: SessionItemRow[]): SessionSnapshot {
  return {
    id: row.id,
    name: row.name,
    status: row.status,
    items: items
      .slice()
      .sort((a, b) => a.sortOrder - b.sortOrder)
      .map(toItem),
    participants: [],
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}
