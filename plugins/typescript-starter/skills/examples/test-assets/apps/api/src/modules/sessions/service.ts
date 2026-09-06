import type {
  CreateSessionInput,
  CreateSessionItemInput,
  SessionId,
  SessionItem,
  SessionItemId,
  SessionSnapshot,
  RevisionedSessionSnapshot,
  SessionSummary,
  UpdateSessionInput,
  UpdateSessionItemInput,
} from '../../types/index';
import type { AppContext } from '../../core/context';
import { AppError } from '../../core/errors';

/**
 * The domain. It owns everything true about a session regardless of who is
 * asking — the controller is a surface that validates, authorises, and
 * delegates in one line.
 *
 * Shape rules, both deliberate:
 *  - methods take **primitives**, never a request or a `Context`. A service that
 *    knows about HTTP cannot be called from the worker or a script;
 *  - methods return data or throw `AppError`. Returning `null` for "missing"
 *    pushes the 404 decision onto every caller, and they decide differently.
 *
 * Participants live on the event bus, not in storage, so the service merges
 * them into the snapshot on the way out. That is the one place the two sources
 * meet, which is why it is here and not in a route handler.
 */
export class SessionService {
  constructor(private readonly ctx: AppContext) {}

  async list(): Promise<{ items: SessionSummary[]; total: number }> {
    const items = (await this.ctx.repositories.sessions.list()).map(
      (summary) => ({
        ...summary,
        participantCount: this.ctx.bus.getConnectionCount(summary.id),
      }),
    );
    return { items, total: items.length };
  }

  async create(input: CreateSessionInput): Promise<SessionSnapshot> {
    const { sessions } = this.ctx.repositories;
    const hardLimit = this.ctx.limits.hardLimit;

    const result = await sessions.createIfBelowLimit(input, hardLimit);
    if (!result) {
      throw AppError.tooManyRequests(
        `Refusing to create a session: hard limit of ${hardLimit} reached.`,
      );
    }

    const { value: snapshot, ...metadata } = result;
    const withParticipants = this.withParticipants(snapshot);

    this.ctx.bus.broadcast(snapshot.id, {
      ...metadata,
      type: 'session_created',
      sessionId: snapshot.id,
      session: withParticipants,
    });
    return withParticipants;
  }

  async get(sessionId: SessionId): Promise<SessionSnapshot> {
    const snapshot = await this.ctx.repositories.sessions.findById(sessionId);
    if (!snapshot) throw notFound(sessionId);

    await this.ctx.repositories.sessions.touch(sessionId);
    return this.withParticipants(snapshot);
  }

  async getRecoverySnapshot(
    sessionId: SessionId,
  ): Promise<RevisionedSessionSnapshot | null> {
    await this.ctx.repositories.sessions.touch(sessionId);
    return this.ctx.repositories.sessions.findRevisionedById(sessionId);
  }

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

  async delete(sessionId: SessionId): Promise<void> {
    const deleted = await this.ctx.repositories.sessions.delete(sessionId);
    if (!deleted) throw notFound(sessionId);

    this.ctx.bus.broadcast(sessionId, {
      type: 'session_deleted',
      sessionId,
      revision: deleted.revision,
      updatedAt: deleted.updatedAt,
    });
    this.ctx.bus.closeSession(sessionId);
  }

  async addItem(
    sessionId: SessionId,
    input: CreateSessionItemInput,
  ): Promise<SessionItem> {
    const result = await this.ctx.repositories.sessions.addItem(
      sessionId,
      input,
    );
    if (!result) throw notFound(sessionId);

    const { value: item, ...metadata } = result;
    this.ctx.bus.broadcast(sessionId, {
      ...metadata,
      type: 'item_added',
      sessionId,
      item,
    });
    return item;
  }

  async updateItem(
    sessionId: SessionId,
    itemId: SessionItemId,
    patch: UpdateSessionItemInput,
  ): Promise<SessionItem> {
    const result = await this.ctx.repositories.sessions.updateItem(
      sessionId,
      itemId,
      patch,
    );
    if (!result) throw itemNotFound(sessionId, itemId);

    const { value: item, ...metadata } = result;
    this.ctx.bus.broadcast(sessionId, {
      ...metadata,
      type: 'item_updated',
      sessionId,
      item,
    });
    return item;
  }

  async removeItem(sessionId: SessionId, itemId: SessionItemId): Promise<void> {
    const removed = await this.ctx.repositories.sessions.removeItem(
      sessionId,
      itemId,
    );
    if (!removed) throw itemNotFound(sessionId, itemId);

    const { value: removedItemId, ...metadata } = removed;
    this.ctx.bus.broadcast(sessionId, {
      ...metadata,
      type: 'item_removed',
      sessionId,
      itemId: removedItemId,
    });
  }

  async exists(sessionId: SessionId): Promise<boolean> {
    return (await this.ctx.repositories.sessions.findById(sessionId)) !== null;
  }

  private withParticipants(snapshot: SessionSnapshot): SessionSnapshot {
    return {
      ...snapshot,
      participants: this.ctx.bus.getParticipants(snapshot.id),
    };
  }
}

function notFound(sessionId: SessionId): AppError {
  return AppError.notFound(`Session ${sessionId} does not exist.`);
}

function itemNotFound(sessionId: SessionId, itemId: SessionItemId): AppError {
  return AppError.notFound(
    `Item ${itemId} does not exist in session ${sessionId}.`,
  );
}
