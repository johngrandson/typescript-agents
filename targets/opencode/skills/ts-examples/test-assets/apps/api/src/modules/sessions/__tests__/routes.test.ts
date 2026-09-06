import { InMemoryJobRepository, InMemorySessionRepository } from '@starter/db';
import { afterAll, beforeEach, describe, expect, it } from 'vitest';
import type { FastifyInstance } from 'fastify';
import type {
  SessionItem,
  SessionSnapshot,
  SessionSummary,
} from '../../../types';
import { buildApp } from '../../../app';
import { SessionEventBus } from '../../../core/eventBus';
import {
  isSessionSnapshot,
  registerContractFormats,
} from '../../../types/validators';

/**
 * Route tests drive a real app through `app.inject()` with an in-memory
 * context: no port, no database, no shared module state between files.
 */
let app: FastifyInstance;
const sessions = new InMemorySessionRepository();

async function createSession(name = 'demo'): Promise<SessionSnapshot> {
  const response = await app.inject({
    method: 'POST',
    url: '/sessions',
    payload: { name },
  });
  return response.json<{ data: SessionSnapshot }>().data;
}

describe('session routes', () => {
  beforeEach(async () => {
    sessions.clear();
    if (!app) {
      app = await buildApp({
        repositories: {
          sessions,
          jobs: new InMemoryJobRepository(),
          driver: 'memory',
          close: async () => {},
        },
        bus: new SessionEventBus(),
        limits: {
          retentionEnabled: true,
          hardLimit: 50,
          idleTimeoutMs: 1_800_000,
          monitorIntervalMs: 60_000,
        },
      });
    }
  });

  afterAll(async () => {
    await app?.close();
  });

  it('creates a session and returns 201 wrapped in { data }', async () => {
    const response = await app.inject({
      method: 'POST',
      url: '/sessions',
      payload: {
        name: 'demo',
        items: [{ kind: 'note', label: 'a', value: '1' }],
      },
    });

    expect(response.statusCode).toBe(201);
    const body = response.json<{ data: SessionSnapshot }>();
    registerContractFormats();
    expect(isSessionSnapshot(body.data)).toBe(true);
    expect(body.data).toMatchObject({ name: 'demo', status: 'idle' });
    expect(body.data.items).toHaveLength(1);
    // The detail envelope carries no `total` — that field would be meaningless.
    expect(body).not.toHaveProperty('total');
  });

  it('rejects an invalid body with the canonical error envelope', async () => {
    const response = await app.inject({
      method: 'POST',
      url: '/sessions',
      payload: { name: '' },
    });

    expect(response.statusCode).toBe(400);
    expect(response.json()).toEqual({
      error: { code: 'VALIDATION_FAILED', message: expect.any(String) },
    });
  });

  it('strips undeclared fields instead of rejecting them (removeAdditional)', async () => {
    const response = await app.inject({
      method: 'POST',
      url: '/sessions',
      payload: { name: 'demo', sneaky: 'dropped' },
    });

    expect(response.statusCode).toBe(201);
    expect(
      response.json<{ data: Record<string, unknown> }>().data,
    ).not.toHaveProperty('sneaky');
  });

  it('404s with a machine-readable code for an unknown session', async () => {
    const response = await app.inject({
      method: 'GET',
      // Well-formed UUID that no session was ever created with — the 404 path,
      // not the format-validation path exercised below.
      url: '/sessions/00000000-0000-0000-0000-000000000000',
    });

    expect(response.statusCode).toBe(404);
    expect(response.json()).toMatchObject({ error: { code: 'NOT_FOUND' } });
  });

  it('400s a malformed session id instead of reaching the driver', async () => {
    const response = await app.inject({ method: 'GET', url: '/sessions/nope' });

    expect(response.statusCode).toBe(400);
    expect(response.json()).toMatchObject({
      error: { code: 'VALIDATION_FAILED' },
    });
  });

  it('lists newest first in the { data, total } envelope', async () => {
    await createSession('first');
    await new Promise((resolve) => setTimeout(resolve, 5));
    await createSession('second');

    const body = await app
      .inject({ method: 'GET', url: '/sessions' })
      .then((response) =>
        response.json<{ data: SessionSummary[]; total: number }>(),
      );

    expect(body.total).toBe(2);
    expect(body.data.map((item) => item.name)).toEqual(['second', 'first']);
  });

  it('applies a partial update without resetting other fields', async () => {
    const session = await createSession('original');

    const response = await app.inject({
      method: 'PATCH',
      url: `/sessions/${session.id}`,
      payload: { status: 'active' },
    });

    expect(response.json<{ data: SessionSnapshot }>().data).toMatchObject({
      name: 'original',
      status: 'active',
    });
  });

  it('preserves explicit false, zero and empty values in an item patch', async () => {
    const session = await createSession();
    const created = await app.inject({
      method: 'POST',
      url: `/sessions/${session.id}/items`,
      payload: { kind: 'task', label: 'keep label', value: 'clear this' },
    });
    const item = created.json<{ data: SessionItem }>().data;
    await app.inject({
      method: 'PATCH',
      url: `/sessions/${session.id}/items/${item.id}`,
      payload: { done: true },
    });
    const patched = await app.inject({
      method: 'PATCH',
      url: `/sessions/${session.id}/items/${item.id}`,
      payload: { done: false, order: 0, value: '' },
    });
    expect(patched.statusCode).toBe(200);
    expect(patched.json<{ data: SessionItem }>().data).toMatchObject({
      kind: 'task',
      label: 'keep label',
      done: false,
      order: 0,
      value: '',
    });
  });

  it('rejects an item without its required value through the HTTP validator', async () => {
    const session = await createSession();
    const response = await app.inject({
      method: 'POST',
      url: `/sessions/${session.id}/items`,
      payload: { kind: 'note', label: 'missing value' },
    });
    expect(response.statusCode).toBe(400);
    expect(response.json()).toMatchObject({
      error: { code: 'VALIDATION_FAILED' },
    });
    expect((await sessions.findById(session.id))?.items).toEqual([]);
  });

  it('rejects an initial batch above the shared contract limit', async () => {
    const response = await app.inject({
      method: 'POST',
      url: '/sessions',
      payload: {
        name: 'oversized',
        items: Array.from({ length: 501 }, () => ({
          kind: 'note',
          label: 'a',
          value: '',
        })),
      },
    });
    expect(response.statusCode).toBe(400);
    expect(await sessions.count()).toBe(0);
  });

  it('adds, reorders, and removes items keeping order contiguous', async () => {
    const session = await createSession();

    const first = await app
      .inject({
        method: 'POST',
        url: `/sessions/${session.id}/items`,
        payload: { kind: 'note', label: 'a', value: '1' },
      })
      .then((response) => response.json<{ data: SessionItem }>().data);

    await app.inject({
      method: 'POST',
      url: `/sessions/${session.id}/items`,
      payload: { kind: 'task', label: 'b', value: '2' },
    });

    const updated = await app
      .inject({
        method: 'PATCH',
        url: `/sessions/${session.id}/items/${first.id}`,
        payload: { done: true, order: 1 },
      })
      .then((response) => response.json<{ data: SessionItem }>().data);

    expect(updated).toMatchObject({ done: true, order: 1, label: 'a' });

    expect(
      (
        await app.inject({
          method: 'DELETE',
          url: `/sessions/${session.id}/items/${first.id}`,
        })
      ).statusCode,
    ).toBe(204);

    const snapshot = await app
      .inject({ method: 'GET', url: `/sessions/${session.id}` })
      .then((response) => response.json<{ data: SessionSnapshot }>().data);

    expect(snapshot.items.map((item) => [item.label, item.order])).toEqual([
      ['b', 0],
    ]);
  });

  it('deletes a session and then 404s on it', async () => {
    const session = await createSession();

    expect(
      (await app.inject({ method: 'DELETE', url: `/sessions/${session.id}` }))
        .statusCode,
    ).toBe(204);
    expect(
      (await app.inject({ method: 'GET', url: `/sessions/${session.id}` }))
        .statusCode,
    ).toBe(404);
  });

  it('reports the active storage driver on the health probe', async () => {
    const health = await app.inject({ method: 'GET', url: '/health' });

    expect(health.json<{ data: { driver: string } }>().data).toMatchObject({
      status: 'ok',
      driver: 'memory',
    });
  });

  it('lists mounted modules in mount order', async () => {
    const modules = await app
      .inject({ method: 'GET', url: '/modules' })
      .then((response) => response.json<{ data: Array<{ id: string }> }>());

    expect(modules.data.map((module) => module.id)).toEqual([
      'health',
      'sessions',
      'storage:templates',
      'storage:layouts',
    ]);
  });

  it('serves an OpenAPI document generated from the route schemas', async () => {
    const spec = await app
      .inject({ method: 'GET', url: '/openapi.json' })
      .then((response) => response.json<{ paths: Record<string, unknown> }>());

    expect(Object.keys(spec.paths)).toEqual(
      expect.arrayContaining(['/sessions', '/sessions/{sessionId}', '/health']),
    );
    expect(spec.paths['/sessions']).toMatchObject({
      get: {
        responses: {
          200: {
            content: {
              'application/json': {
                schema: {
                  required: ['data', 'total'],
                  properties: {
                    total: { type: 'integer', minimum: 0 },
                    data: {
                      type: 'array',
                      items: {
                        properties: {
                          itemCount: { type: 'integer', minimum: 0 },
                          createdAt: { type: 'string', format: 'date-time' },
                        },
                      },
                    },
                  },
                },
              },
            },
          },
        },
      },
    });
    expect(spec.paths['/sessions/{sessionId}']).toMatchObject({
      get: {
        responses: {
          200: {
            content: {
              'application/json': {
                schema: {
                  properties: {
                    data: {
                      properties: {
                        items: {
                          type: 'array',
                          items: {
                            properties: {
                              done: { type: 'boolean' },
                              order: { type: 'integer', minimum: 0 },
                            },
                          },
                        },
                        participants: { type: 'array' },
                      },
                    },
                  },
                },
              },
            },
          },
          404: {
            content: {
              'application/json': {
                schema: {
                  properties: { error: { required: ['code', 'message'] } },
                },
              },
            },
          },
        },
      },
    });
    expect(spec.paths['/templates']).toMatchObject({
      get: {
        responses: {
          200: {
            content: {
              'application/json': {
                schema: {
                  properties: {
                    data: {
                      items: {
                        properties: {
                          sizeBytes: { type: 'integer', minimum: 0 },
                          savedAt: { type: 'string' },
                        },
                      },
                    },
                  },
                },
              },
            },
          },
        },
      },
    });
  });

  it('returns a typed 404 for an unrouted path', async () => {
    const response = await app.inject({ method: 'GET', url: '/nope' });

    expect(response.statusCode).toBe(404);
    expect(response.json()).toMatchObject({ error: { code: 'NOT_FOUND' } });
  });
});
