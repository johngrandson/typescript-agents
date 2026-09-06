import type { Static } from '@sinclair/typebox';
import type {
  CreateSessionItemSchema,
  CreateSessionSchema,
  UpdateSessionItemSchema,
  UpdateSessionSchema,
  SessionItemSchema,
  SessionParticipantSchema,
  SessionSnapshotSchema,
  SessionSummarySchema,
} from './schemas/session.js';

/**
 * The reference domain. It is deliberately generic: rename `Session` to your
 * real aggregate and the surrounding layers keep working unchanged.
 */

export type SessionId = string;
export type SessionItemId = string;

export const SESSION_STATUSES = ['idle', 'active', 'closed'] as const;
export type SessionStatus = (typeof SESSION_STATUSES)[number];

export const SESSION_ITEM_KINDS = ['note', 'task', 'link'] as const;
export type SessionItemKind = (typeof SESSION_ITEM_KINDS)[number];

export type SessionItem = Static<typeof SessionItemSchema>;

/** A live client attached to a session over WebSocket. */
export type SessionParticipant = Static<typeof SessionParticipantSchema>;

/**
 * Public DTO of a session.
 *
 * Keep this complete: when the API maps internal state to this type, every
 * field the web/mobile clients read must be present. A missing field is a
 * silent regression, not a compile error.
 */
export type SessionSnapshot = Static<typeof SessionSnapshotSchema>;

/** Cheap projection for list views — no items, no participants. */
export type SessionSummary = Static<typeof SessionSummarySchema>;

/** Runtime definitions live in the explicit @starter/types/schemas entry point. */
export type CreateSessionInput = Static<typeof CreateSessionSchema>;

/** Partial by design: only the fields actually sent are applied. */
export type UpdateSessionInput = Static<typeof UpdateSessionSchema>;

export type CreateSessionItemInput = Static<typeof CreateSessionItemSchema>;

export type UpdateSessionItemInput = Static<typeof UpdateSessionItemSchema>;
