import path from 'node:path';
import { createJsonDocumentStore, DocumentStoreError } from '@starter/db';
import { env } from '@starter/env';
import {
  isSessionSnapshot,
  registerContractFormats,
} from '../types/validators';
import { PermanentJobError } from '../errors';
import type { JobHandler } from '../registry';

const uuid =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** Validate the archived snapshot and immutable publication identity together. */
function isArchive(value: unknown, sessionId: string, jobId: string): boolean {
  return (
    record(value) &&
    value.jobId === jobId &&
    isSessionSnapshot(value.session) &&
    value.name === value.session.name &&
    value.session.id === sessionId &&
    value.session.items.every((item) => uuid.test(item.id))
  );
}

/** The directory and filesystem boundary are injectable; constructing a handler performs no I/O. */
export function createArchiveSessionHandler(
  dataDir = env.STARTER_DATA_DIR,
  openStore: typeof createJsonDocumentStore = createJsonDocumentStore,
): JobHandler {
  registerContractFormats();
  return {
    kind: 'session.archive',
    description: 'Publish one immutable session snapshot per job.',

    async handle(payload, ctx) {
      ctx.signal.throwIfAborted();
      if (
        !record(payload) ||
        typeof payload.sessionId !== 'string' ||
        !uuid.test(payload.sessionId)
      ) {
        throw new PermanentJobError(
          'archive-session requires a UUID sessionId payload.',
        );
      }
      if (typeof ctx.job.id !== 'string' || !uuid.test(ctx.job.id)) {
        throw new PermanentJobError(
          'archive-session requires a UUID job identity.',
        );
      }
      const sessionId = payload.sessionId.toLowerCase();
      const jobId = ctx.job.id.toLowerCase();

      const fileName = `session-${sessionId}-job-${jobId}.json`;
      const store = await openStore({
        dirPath: path.join(dataDir, 'archives'),
        filePrefix: 'session-',
        accepts: (value) => isArchive(value, sessionId, jobId),
      });
      ctx.signal.throwIfAborted();
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

      if (await alreadyPublished()) {
        ctx.log.info('archive already published', {
          sessionId,
          jobId,
          fileName,
        });
        return;
      }
      ctx.signal.throwIfAborted();
      const snapshot = await ctx.repositories.sessions.findById(sessionId);
      ctx.signal.throwIfAborted();
      if (!snapshot) {
        ctx.log.info('archive skipped, session no longer exists', {
          sessionId,
          jobId,
        });
        return;
      }

      ctx.signal.throwIfAborted();
      try {
        await store.create(
          { name: snapshot.name, jobId, session: snapshot },
          fileName,
        );
      } catch (error) {
        ctx.signal.throwIfAborted();
        // Another attempt can win publication after our initial read. Only a
        // validated archive for this exact identity counts as the same effect.
        if (
          !(error instanceof DocumentStoreError) ||
          error.kind !== 'already-exists' ||
          !(await alreadyPublished())
        )
          throw error;
      }
      ctx.signal.throwIfAborted();
      ctx.log.info('session archived', { sessionId, jobId, fileName });
    },
  };
}

export const archiveSessionHandler = createArchiveSessionHandler();
