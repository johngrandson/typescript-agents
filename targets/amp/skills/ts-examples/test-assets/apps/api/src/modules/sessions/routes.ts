import { randomUUID } from 'node:crypto';
import type { FastifyPluginAsyncTypebox } from '@fastify/type-provider-typebox';
import type { SessionWebSocket } from '../../core/eventBus';
import type { AppContext } from '../../core/context';
import { createWebSocketSocket } from '../../core/webSocket';
import { createSseSocket } from '../../core/sseSocket';
import { SessionService } from './service';
import {
  CreateSessionItemSchema,
  CreateSessionSchema,
  ErrorResponseSchema,
  SessionDetailSchema,
  SessionItemDetailSchema,
  SessionItemParamsSchema,
  SessionListSchema,
  SessionParamsSchema,
  type SessionParams,
  SessionStreamQuerySchema,
  type SessionStreamQuery,
  UpdateSessionItemSchema,
  UpdateSessionSchema,
} from './schemas';

/**
 * The HTTP surface for sessions.
 *
 * Every handler is the same three moves: the schema validates, the service
 * decides, the envelope wraps. Any logic that appears here instead of in
 * `service.ts` becomes logic the worker and the scripts cannot reach.
 */
export function createSessionRoutes(
  ctx: AppContext,
): FastifyPluginAsyncTypebox {
  const service = new SessionService(ctx);
  function subscribe(
    sessionId: string,
    clientId: string,
    socket: SessionWebSocket,
    protocol: SessionStreamQuery['protocol'],
  ) {
    if (protocol === '2') {
      ctx.bus.subscribeV2(sessionId, clientId, socket, () =>
        service.getRecoverySnapshot(sessionId),
      );
    } else ctx.bus.subscribe(sessionId, clientId, socket);
  }

  return async (app) => {
    app.get(
      '/sessions',
      {
        schema: {
          summary: 'List sessions, newest first.',
          tags: ['sessions'],
          response: { 200: SessionListSchema },
        },
      },
      async () => {
        const { items, total } = await service.list();
        return { data: items, total };
      },
    );

    app.post(
      '/sessions',
      {
        schema: {
          summary: 'Create a session.',
          tags: ['sessions'],
          body: CreateSessionSchema,
          response: { 201: SessionDetailSchema, 429: ErrorResponseSchema },
        },
      },
      async (request, reply) =>
        reply.code(201).send({ data: await service.create(request.body) }),
    );

    app.get(
      '/sessions/:sessionId',
      {
        schema: {
          summary: 'Full snapshot of one session.',
          tags: ['sessions'],
          params: SessionParamsSchema,
          response: { 200: SessionDetailSchema, 404: ErrorResponseSchema },
        },
      },
      async (request) => ({
        data: await service.get(request.params.sessionId),
      }),
    );

    app.patch(
      '/sessions/:sessionId',
      {
        schema: {
          summary: 'Partial update — omitted fields are preserved.',
          tags: ['sessions'],
          params: SessionParamsSchema,
          body: UpdateSessionSchema,
          response: { 200: SessionDetailSchema, 404: ErrorResponseSchema },
        },
      },
      async (request) => ({
        data: await service.update(request.params.sessionId, request.body),
      }),
    );

    app.delete(
      '/sessions/:sessionId',
      {
        schema: {
          summary: 'Delete a session and disconnect its subscribers.',
          tags: ['sessions'],
          params: SessionParamsSchema,
          response: { 204: { type: 'null' }, 404: ErrorResponseSchema },
        },
      },
      async (request, reply) => {
        await service.delete(request.params.sessionId);
        return reply.code(204).send();
      },
    );

    app.post(
      '/sessions/:sessionId/items',
      {
        schema: {
          summary: 'Append an item.',
          tags: ['sessions'],
          params: SessionParamsSchema,
          body: CreateSessionItemSchema,
          response: { 201: SessionItemDetailSchema, 404: ErrorResponseSchema },
        },
      },
      async (request, reply) =>
        reply.code(201).send({
          data: await service.addItem(request.params.sessionId, request.body),
        }),
    );

    app.patch(
      '/sessions/:sessionId/items/:itemId',
      {
        schema: {
          summary: 'Partial update of an item; `order` reorders the list.',
          tags: ['sessions'],
          params: SessionItemParamsSchema,
          body: UpdateSessionItemSchema,
          response: { 200: SessionItemDetailSchema, 404: ErrorResponseSchema },
        },
      },
      async (request) => ({
        data: await service.updateItem(
          request.params.sessionId,
          request.params.itemId,
          request.body,
        ),
      }),
    );

    app.delete(
      '/sessions/:sessionId/items/:itemId',
      {
        schema: {
          summary: 'Remove an item and reindex the remaining ones.',
          tags: ['sessions'],
          params: SessionItemParamsSchema,
          response: { 204: { type: 'null' }, 404: ErrorResponseSchema },
        },
      },
      async (request, reply) => {
        await service.removeItem(
          request.params.sessionId,
          request.params.itemId,
        );
        return reply.code(204).send();
      },
    );

    // --- realtime --------------------------------------------------------
    // Both transports hand the *same* structural socket to the bus.

    app.get(
      '/sessions/:sessionId/events',
      {
        schema: {
          summary: 'Server-Sent Events stream of session events.',
          querystring: SessionStreamQuerySchema,
          tags: ['sessions'],
          params: SessionParamsSchema,
        },
      },
      async (request, reply) => {
        const { sessionId } = request.params;
        if (request.query.protocol !== '2') await service.get(sessionId);
        const clientId = randomUUID();
        subscribe(
          sessionId,
          clientId,
          createSseSocket(reply, { sessionId, clientId }),
          request.query.protocol,
        );
        return reply;
      },
    );

    app.get<{ Params: SessionParams; Querystring: SessionStreamQuery }>(
      '/sessions/:sessionId/ws',
      {
        websocket: true,
        schema: {
          params: SessionParamsSchema,
          querystring: SessionStreamQuerySchema,
          tags: ['sessions'],
        },
        // Validate negotiation before upgrade; legacy lookup retains its HTTP errors.
        // V2 subscribes before reading, including authoritative absence.
        preHandler: async (request) => {
          if (request.query.protocol !== '2')
            await service.get(request.params.sessionId);
        },
      },
      (connection, request) => {
        const { sessionId } = request.params;
        const clientId = randomUUID();
        subscribe(
          sessionId,
          clientId,
          createWebSocketSocket(connection, { sessionId, clientId }),
          request.query.protocol,
        );
      },
    );
  };
}
