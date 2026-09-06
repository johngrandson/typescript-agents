import {
  Array as ArrayType,
  Integer,
  Object as ObjectType,
  String as StringType,
  type TSchema,
} from '@sinclair/typebox';

/** Request IDs use UUID format validation at the transport boundary. */
export const UuidSchema = StringType({ format: 'uuid' });

/** The canonical detail envelope; each concrete resource supplies its schema. */
export const DetailOf = <T extends TSchema>(schema: T) =>
  ObjectType({ data: schema });

/** List totals retain the existing numeric wire contract. */
export const ListOf = <T extends TSchema>(schema: T) =>
  ObjectType({
    data: ArrayType(schema),
    total: Integer({ minimum: 0 }),
  });

export const ErrorResponseSchema = ObjectType({
  error: ObjectType({
    code: StringType({ description: 'Branch on this, never on the message.' }),
    message: StringType(),
  }),
});

/** Session timestamps keep the existing OpenAPI date-time contract. */
export const IsoDateSchema = StringType({ format: 'date-time' });
