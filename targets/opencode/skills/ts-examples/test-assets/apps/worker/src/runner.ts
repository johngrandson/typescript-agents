import { randomUUID } from 'node:crypto';
import { performance } from 'node:perf_hooks';
import {
  databaseErrorMessage,
  type ClaimedJob,
  type Repositories,
} from '@starter/db';
import { env } from '@starter/env';
import { getLogger } from '@starter/logger';
import type { JobContext, JobRegistry } from './registry';
import { PermanentJobError } from './errors';

/** @public */
export interface RunnerOptions {
  pollIntervalMs: number;
  /** Maximum executions per tick; jobs are claimed one at a time. */
  batchSize: number;
  retryBaseMs?: number;
  leaseMs?: number;
  handlerTimeoutMs?: number;
  shutdownTimeoutMs?: number;
  rpcTimeoutMs?: number;
  /** Enter the process shutdown boundary; it must await stop before closing storage. */
  onFatal?: () => void;
}
interface TickResult {
  processed: number;
  failed: number;
}
class ExecutionStopped extends Error {}

/** Sequential, fenced, at-least-once execution with a bounded active attempt. */
export class JobRunner {
  private readonly log = getLogger(['worker', 'runner']);
  private readonly workerId = `worker-${randomUUID().slice(0, 8)}`;
  private timer: NodeJS.Timeout | null = null;
  private active: Promise<TickResult> | null = null;
  private activeAbort: AbortController | null = null;
  private stopped = false;
  private fatal = false;
  private readonly leaseMs: number;
  private readonly handlerTimeoutMs: number;
  private readonly rpcTimeoutMs: number;

  constructor(
    private readonly repositories: Repositories,
    private readonly registry: JobRegistry,
    private readonly options: RunnerOptions,
  ) {
    this.leaseMs = options.leaseMs ?? env.WORKER_LEASE_MS;
    this.handlerTimeoutMs =
      options.handlerTimeoutMs ?? env.WORKER_HANDLER_TIMEOUT_MS;
    this.rpcTimeoutMs = options.rpcTimeoutMs ?? env.WORKER_RPC_TIMEOUT_MS;
    const shutdownMs =
      options.shutdownTimeoutMs ?? env.WORKER_SHUTDOWN_TIMEOUT_MS;
    for (const value of [
      this.leaseMs,
      this.handlerTimeoutMs,
      this.rpcTimeoutMs,
      shutdownMs,
    ]) {
      if (!Number.isSafeInteger(value) || value < 1 || value > 3_600_000)
        throw new RangeError(
          'Worker timing values must be bounded positive integers.',
        );
    }
    if (this.leaseMs <= this.handlerTimeoutMs + shutdownMs + this.rpcTimeoutMs)
      throw new RangeError(
        'Worker lease must exceed handler, shutdown and RPC timeouts.',
      );
  }

  get id(): string {
    return this.workerId;
  }

  start(): void {
    if (this.timer || this.stopped) return;
    this.log.info('worker started', {
      workerId: this.workerId,
      kinds: this.registry.kinds(),
    });
    this.timer = setInterval(() => {
      void this.tick().catch((error: unknown) => {
        this.log.error('worker poll failed', {
          error: databaseErrorMessage(error) ?? error,
        });
      });
    }, this.options.pollIntervalMs);
  }

  /** Terminal stop: finish the current claim/attempt, without claiming waiting work. */
  async stop(): Promise<void> {
    this.stopPolling();
    await this.active;
  }

  tick(): Promise<TickResult> {
    if (this.stopped || this.active)
      return Promise.resolve({ processed: 0, failed: 0 });
    this.active = this.drainBatch().finally(() => {
      this.active = null;
    });
    return this.active;
  }

  private stopPolling(): void {
    this.stopped = true;
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }

  private stopFatally(operation: string, error?: unknown): void {
    if (this.fatal) return;
    this.fatal = true;
    this.stopPolling();
    this.activeAbort?.abort(new ExecutionStopped('Worker attempt cancelled.'));
    this.log.error('worker ownership or execution deadline failed', {
      operation,
      ...(error === undefined
        ? {}
        : {
            error: databaseErrorMessage(error) ?? error,
          }),
    });
    this.options.onFatal?.();
  }

  /** Keep awaiting the real RPC after timeout; no detached race can release its pool. */
  private async rpc<T>(
    operation: string,
    call: () => Promise<T>,
    fatalOnError = true,
  ): Promise<T> {
    const started = performance.now();
    const deadline = setTimeout(
      () => this.stopFatally(operation),
      this.rpcTimeoutMs,
    );
    try {
      const result = await call();
      if (performance.now() - started >= this.rpcTimeoutMs)
        this.stopFatally(operation);
      if (this.fatal) throw new ExecutionStopped();
      return result;
    } catch (error) {
      if (fatalOnError || performance.now() - started >= this.rpcTimeoutMs)
        this.stopFatally(operation, error);
      if (this.fatal) throw new ExecutionStopped();
      throw error;
    } finally {
      clearTimeout(deadline);
    }
  }

  private async acknowledge(
    operation: string,
    call: () => Promise<boolean>,
  ): Promise<void> {
    if (!(await this.rpc(operation, call))) {
      this.stopFatally(operation);
      throw new ExecutionStopped();
    }
  }

  private async drainBatch(): Promise<TickResult> {
    let processed = 0;
    let failed = 0;
    try {
      for (
        let index = 0;
        index < this.options.batchSize && !this.stopped;
        index++
      ) {
        const [job] = await this.rpc(
          'claim',
          () => this.repositories.jobs.claim(this.workerId, 1, this.leaseMs),
          false,
        );
        if (!job) break;
        // A normal stop drains this claim, including a claim already in flight.
        // A fatal stop has already been checked by rpc and starts no handler.
        const ownership = { id: job.id, token: job.ownershipToken };
        await this.acknowledge('renew', () =>
          this.repositories.jobs.renew(ownership, this.leaseMs),
        );
        const handler = this.registry.get(job.kind);
        if (!handler) {
          this.log.error('no handler for job kind', {
            kind: job.kind,
            id: job.id,
          });
          await this.acknowledge('abandon', () =>
            this.repositories.jobs.abandon(
              ownership,
              `No handler for "${job.kind}"`,
            ),
          );
          failed++;
          continue;
        }
        const abort = new AbortController();
        this.activeAbort = abort;
        const started = performance.now();
        const deadline = setTimeout(
          () => this.stopFatally('handler'),
          this.handlerTimeoutMs,
        );
        let handlerFailed = false;
        let failure: unknown;
        try {
          await handler.handle(job.payload, this.context(job, abort.signal));
        } catch (error) {
          handlerFailed = true;
          failure = error;
        } finally {
          clearTimeout(deadline);
          if (performance.now() - started >= this.handlerTimeoutMs)
            this.stopFatally('handler');
          this.activeAbort = null;
        }
        if (this.fatal) throw new ExecutionStopped();
        if (handlerFailed) {
          const message =
            databaseErrorMessage(failure) ??
            (failure instanceof Error ? failure.message : String(failure));
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
          failed++;
        } else {
          // An ambiguous completion must never fall through to failure/retry.
          await this.acknowledge('complete', () =>
            this.repositories.jobs.complete(ownership),
          );
          processed++;
        }
      }
    } catch (error) {
      if (!(error instanceof ExecutionStopped)) throw error;
      failed++;
    }
    return { processed, failed };
  }

  private backoffFor(attempt: number): number {
    return Math.min(
      (this.options.retryBaseMs ?? 1_000) * 2 ** Math.max(0, attempt - 1),
      5 * 60_000,
    );
  }

  private context(job: ClaimedJob, signal: AbortSignal): JobContext {
    return {
      job: { id: job.id, attempts: job.attempts, maxAttempts: job.maxAttempts },
      signal,
      repositories: this.repositories,
      log: this.log,
      enqueue: async (kind, payload, options) => {
        signal.throwIfAborted();
        const id = await this.rpc(
          'enqueue',
          () => this.repositories.jobs.enqueue(kind, payload, options),
          false,
        );
        signal.throwIfAborted();
        return id;
      },
    };
  }
}
