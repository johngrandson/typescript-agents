import type { NextRequest } from 'next/server';
import { getServerSideApiUrl } from '@/lib/server-url.server';
import { createRequestDeadline } from '@/lib/request-deadline';
import { isErrorResponse } from '@/lib/types/validators';

/**
 * BFF proxy for the API's SSE stream.
 *
 * Why proxy at all: the browser then talks only to its own origin — no CORS
 * dance, no API URL in client bundles, and a single place to add auth headers
 * later. The response body is piped through untouched so backpressure and
 * disconnects still propagate.
 */
export const dynamic = 'force-dynamic';

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ sessionId: string }> },
): Promise<Response> {
  const { sessionId } = await context.params;

  const baseUrl = getServerSideApiUrl();
  const protocol = request.nextUrl.searchParams.getAll('protocol');
  const query = new URLSearchParams();
  for (const value of protocol) query.append('protocol', value);
  const streamUrl = `${baseUrl}/sessions/${encodeURIComponent(sessionId)}/events${query.size ? `?${query}` : ''}`;
  const deadline = createRequestDeadline(10_000, request.signal);
  try {
    deadline.signal.throwIfAborted();
    const upstream = await fetch(streamUrl, {
      headers: { Accept: 'text/event-stream' },
      signal: deadline.signal,
      cache: 'no-store',
    });

    if (!upstream.ok) {
      let payload: unknown;
      try {
        payload = await upstream.json();
      } catch (error) {
        if (deadline.signal.aborted || !(error instanceof SyntaxError))
          throw error;
        payload = null;
      }
      const headers = new Headers({ 'Cache-Control': 'no-store' });
      const retryAfter = upstream.headers.get('Retry-After');
      if (retryAfter !== null) headers.set('Retry-After', retryAfter);
      return Response.json(
        isErrorResponse(payload)
          ? {
              error: {
                code: payload.error.code,
                message: payload.error.message,
              },
            }
          : {
              error: {
                code: 'UPSTREAM_INVALID_RESPONSE',
                message: 'The API returned an invalid response.',
              },
            },
        { status: upstream.status, headers },
      );
    }

    if (
      upstream.status !== 200 ||
      !upstream.body ||
      upstream.headers
        .get('Content-Type')
        ?.split(';')[0]
        ?.trim()
        .toLowerCase() !== 'text/event-stream'
    ) {
      await upstream.body?.cancel();
      return failure(
        502,
        'UPSTREAM_INVALID_RESPONSE',
        'The API returned an invalid response.',
      );
    }
    // No response-wide deadline: the composed signal still follows the caller,
    // and reusing the body preserves cancellation and native stream pressure.
    return new Response(upstream.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        Connection: 'keep-alive',
        'X-Accel-Buffering': 'no',
      },
    });
  } catch {
    if (deadline.signal.aborted) {
      return deadline.timedOut()
        ? failure(
            504,
            'UPSTREAM_TIMEOUT',
            'Opening the event stream timed out.',
          )
        : failure(499, 'REQUEST_ABORTED', 'The request was cancelled.');
    }
    return failure(
      502,
      'UPSTREAM_UNAVAILABLE',
      'Could not open the event stream.',
    );
  } finally {
    // This clears only the timer, leaving caller cancellation connected.
    deadline.dispose();
  }
}

function failure(status: number, code: string, message: string): Response {
  return Response.json(
    { error: { code, message } },
    { status, headers: { 'Cache-Control': 'no-store' } },
  );
}
