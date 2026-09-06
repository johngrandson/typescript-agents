import { DrizzleQueryError } from 'drizzle-orm';

/**
 * Drizzle's message contains SQL and bound values. Only the driver's SQLSTATE
 * is safe to retain here; other errors keep their boundary's existing policy.
 */
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
