import {
  Array as ArrayType,
  Boolean as BooleanType,
  Integer,
  Literal,
  Null,
  Object as ObjectType,
  Optional,
  String as StringType,
  Union,
  type Static,
} from '@sinclair/typebox';
import { SESSION_ITEM_KINDS, SESSION_STATUSES } from '../session.js';
import { IsoDateSchema, UuidSchema } from './common.js';

export const SessionItemKindSchema = Union(
  SESSION_ITEM_KINDS.map((kind) => Literal(kind)),
  { description: 'What the item represents.' },
);

export const SessionStatusSchema = Union(
  SESSION_STATUSES.map((status) => Literal(status)),
);

export const CreateSessionItemSchema = ObjectType(
  {
    kind: SessionItemKindSchema,
    label: StringType({ minLength: 1, maxLength: 200 }),
    value: StringType({ maxLength: 4_000 }),
  },
  { additionalProperties: false },
);

export const CreateSessionSchema = ObjectType(
  {
    name: StringType({ minLength: 1, maxLength: 200 }),
    items: Optional(ArrayType(CreateSessionItemSchema, { maxItems: 500 })),
  },
  { additionalProperties: false },
);

/** Omitted fields must remain absent so partial updates preserve stored data. */
export const UpdateSessionSchema = ObjectType(
  {
    name: Optional(StringType({ minLength: 1, maxLength: 200 })),
    status: Optional(SessionStatusSchema),
  },
  { additionalProperties: false },
);

export const UpdateSessionItemSchema = ObjectType(
  {
    kind: Optional(SessionItemKindSchema),
    label: Optional(StringType({ minLength: 1, maxLength: 200 })),
    value: Optional(StringType({ maxLength: 4_000 })),
    done: Optional(BooleanType()),
    order: Optional(Integer({ minimum: 0 })),
  },
  { additionalProperties: false },
);

export const SessionParamsSchema = ObjectType({ sessionId: UuidSchema });
export const SessionItemParamsSchema = ObjectType({
  sessionId: UuidSchema,
  itemId: UuidSchema,
});

export type SessionParams = Static<typeof SessionParamsSchema>;
export type SessionItemParams = Static<typeof SessionItemParamsSchema>;

export const SessionItemSchema = ObjectType({
  id: StringType(),
  kind: SessionItemKindSchema,
  label: StringType(),
  value: StringType(),
  order: Integer({ minimum: 0 }),
  done: BooleanType(),
  createdAt: IsoDateSchema,
  updatedAt: IsoDateSchema,
});

export const SessionParticipantSchema = ObjectType({
  clientId: StringType(),
  name: Union([StringType(), Null()]),
});

export const SessionSnapshotSchema = ObjectType({
  id: StringType(),
  name: StringType(),
  status: SessionStatusSchema,
  items: ArrayType(SessionItemSchema),
  participants: ArrayType(SessionParticipantSchema),
  createdAt: IsoDateSchema,
  updatedAt: IsoDateSchema,
});

export const SessionSummarySchema = ObjectType({
  id: StringType(),
  name: StringType(),
  status: SessionStatusSchema,
  itemCount: Integer({ minimum: 0 }),
  participantCount: Integer({ minimum: 0 }),
  createdAt: IsoDateSchema,
  updatedAt: IsoDateSchema,
});
