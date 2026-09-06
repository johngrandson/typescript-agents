---
name: ts-narrow-catch
description: Use when auditing broad catch blocks that swallow programmer errors,
  misclassify unknown…
---

# Narrow unknown catches

Read the full catch boundary and every operation inside its try block. Classify only failures the caller intentionally handles; preserve programmer errors and unrelated infrastructure failures.

## Usage

```text
pnpm --filter @starter/worker test:run src/handlers/__tests__/archive-session.test.ts
```

## Procedure

1. Identify the intended outcome for each expected error. Look up existing predicates/classes in `apps/api/src/core/errors.ts`, `packages/db/src/errors.ts`,
   `packages/db/src/document-store.ts` and `apps/worker/src/errors.ts`.
2. Keep the catch input `unknown`. Narrow with a real class or discriminant; a type cast or message substring is not proof of error identity.
3. Restrict the try block to the operation whose failure is expected. Preserve `AppError` and rethrow unexpected errors. Use `finally` for cleanup without replacing the original failure.
4. In workers, distinguish permanent payload errors from retryable failures and ownership loss. Never convert ambiguous completion into another `fail` acknowledgement.
5. Add a test showing the expected failure is handled and an unexpected `Error` still escapes. Verify cancellation is checked before an error is transformed.

The archive handler deliberately turns only a `DocumentStoreError` of kind `not-found` into absence, and treats an invalid existing archive as a permanent error. Other errors
propagate. Use that boundary as the example, not a blanket `catch { return null }`.

API error serialization is a top-level catch by design; keep deployed messages sanitized and test INTERNAL output. Do not mechanically remove a boundary whose purpose is safe error reporting.

## Starter example

This excerpt uses the existing implementation; read its source for imports and setup.

Source: `apps/worker/src/handlers/archive-session.ts`.

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

## Iron Laws

- Verify the actual workspace and cited source before applying the recipe.
- Preserve the domain, platform and runtime limits stated above; a missing capability is not an installed framework.
- Keep failures and unexecuted checks visible. Never bypass tests or reset a database to obtain a passing result.

## References

- [Patterns](references/patterns.md)
- [Taxonomy](references/taxonomy.md)
