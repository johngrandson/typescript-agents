import type {
  SessionEvent,
  SessionParticipant,
  SessionSnapshot,
} from './index.js';

/**
 * Pure projection of a server event onto a local snapshot.
 *
 * This lives in the contracts package, not in an app, because *every* client
 * has to agree on what "apply this event" means. Duplicating it in the web app
 * and the mobile app is how two clients slowly start showing different lists
 * from the same stream.
 *
 * The reference project does the same thing with its layout maths — contracts
 * plus the pure functions that operate on them, never I/O.
 */
export function applySessionEvent(
  snapshot: SessionSnapshot,
  event: SessionEvent,
): SessionSnapshot {
  // Events addressed to another session must never mutate this one.
  if ('sessionId' in event && event.sessionId !== snapshot.id) return snapshot;

  switch (event.type) {
    case 'connected':
      return snapshot;

    case 'session_created':
    case 'session_updated':
      // The server sends a complete snapshot; participants ride along with it.
      return event.session;

    case 'session_deleted':
      return { ...snapshot, status: 'closed' };

    case 'item_added':
      return snapshot.items.some((item) => item.id === event.item.id)
        ? snapshot
        : { ...snapshot, items: sortItems([...snapshot.items, event.item]) };

    case 'item_updated': {
      const current = snapshot.items.find((item) => item.id === event.item.id);
      const replaced = snapshot.items.map((item) =>
        item.id === event.item.id ? event.item : item,
      );

      // A changed `order` is a move, not a sort-key edit: the neighbours shift
      // too. Sorting alone leaves two items claiming the same slot, with the
      // tie broken arbitrarily.
      return {
        ...snapshot,
        items:
          current && current.order !== event.item.order
            ? moveWithin(replaced, event.item.id, event.item.order)
            : sortItems(replaced),
      };
    }

    case 'item_removed':
      return {
        ...snapshot,
        items: reindex(
          snapshot.items.filter((item) => item.id !== event.itemId),
        ),
      };

    case 'participants_updated':
      return {
        ...snapshot,
        participants: dedupeParticipants(event.participants),
      };
  }
}

function sortItems<T extends { order: number }>(items: T[]): T[] {
  return [...items].sort((a, b) => a.order - b.order);
}

/**
 * The server reindexes on removal and re-broadcasts, but the removal event
 * itself carries only an id — reindexing locally keeps the list contiguous
 * between the two messages instead of flashing a gap.
 */
function reindex<T extends { order: number }>(items: T[]): T[] {
  return sortItems(items).map((item, order) =>
    item.order === order ? item : { ...item, order },
  );
}

/** Pull `id` out of the list and reinsert it at `targetOrder`, then reindex. */
function moveWithin<T extends { id: string; order: number }>(
  items: T[],
  id: string,
  targetOrder: number,
): T[] {
  const ordered = sortItems(items);
  const from = ordered.findIndex((item) => item.id === id);
  if (from === -1) return ordered;

  const to = Math.max(0, Math.min(targetOrder, ordered.length - 1));
  const [moved] = ordered.splice(from, 1);
  if (!moved) return ordered;
  ordered.splice(to, 0, moved);

  return ordered.map((item, order) =>
    item.order === order ? item : { ...item, order },
  );
}

function dedupeParticipants(
  participants: SessionParticipant[],
): SessionParticipant[] {
  const seen = new Map<string, SessionParticipant>();
  for (const participant of participants) {
    seen.set(participant.clientId, participant);
  }
  return [...seen.values()];
}
