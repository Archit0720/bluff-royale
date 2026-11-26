declare const process: { env: Record<string, string | undefined> };

type IncomingMessage = AsyncIterable<string | Uint8Array> & {
  url?: string;
  method?: string;
  body?: unknown;
  headers: Record<string, string | string[] | undefined>;
};

type ServerResponse = {
  statusCode: number;
  setHeader: (name: string, value: string | string[]) => void;
  end: (body?: string | Uint8Array) => void;
};

const allowedRoutes = [
  /^\/auth\/(nonce|google|me|logout|me\/matches)$/,
  /^\/games(?:\/[A-Z0-9]+(?:\/(join|start|state|play|skip|close-round|challenge|pause|resume|emote))?)?$/,
];

export default async function handler(
  request: IncomingMessage,
  response: ServerResponse,
) {
  const apiOrigin = process.env.BLUFF_API_ORIGIN;
  if (!apiOrigin) {
    response.statusCode = 503;
    response.end('The game API proxy is not configured.');
    return;
  }

  let upstreamOrigin: URL;
  try {
    upstreamOrigin = new URL(apiOrigin);
  } catch {
    response.statusCode = 500;
    response.end('The game API proxy configuration is invalid.');
    return;
  }
  if (upstreamOrigin.protocol !== 'https:' || upstreamOrigin.pathname !== '/') {
    response.statusCode = 500;
    response.end('The game API origin must be an HTTPS origin without a path.');
    return;
  }

  const incoming = new URL(request.url || '/', 'https://vercel.invalid');
  const rewrittenPath = incoming.searchParams.get('__api_path');
  const apiPath =
    rewrittenPath === null
      ? incoming.pathname.replace(/^\/api(?=\/|$)/, '') || '/'
      : `/${rewrittenPath.replace(/^\/+/, '')}`;
  if (!allowedRoutes.some((route) => route.test(apiPath))) {
    response.statusCode = 404;
    response.end('API route not found.');
    return;
  }

  const method = request.method || 'GET';
  if (!['GET', 'POST', 'OPTIONS'].includes(method)) {
    response.statusCode = 405;
    response.setHeader('Allow', 'GET, POST, OPTIONS');
    response.end('Method not allowed.');
    return;
  }

  try {
    const chunks: Uint8Array[] = [];
    let size = 0;
    const parsedBody = request.body;
    const serializedBody =
      parsedBody === undefined
        ? undefined
        : typeof parsedBody === 'string'
          ? parsedBody
          : JSON.stringify(parsedBody);
    if (serializedBody !== undefined) {
      chunks.push(new TextEncoder().encode(serializedBody));
      size = chunks[0].byteLength;
    } else {
      for await (const chunk of request) {
        const bytes = typeof chunk === 'string' ? new TextEncoder().encode(chunk) : chunk;
        size += bytes.byteLength;
        if (size > 100_000) {
          response.statusCode = 413;
          response.end('Request body is too large.');
          return;
        }
        chunks.push(bytes);
      }
    }
    if (size > 100_000) {
      response.statusCode = 413;
      response.end('Request body is too large.');
      return;
    }
    const body = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      body.set(chunk, offset);
      offset += chunk.byteLength;
    }

    const headers = new Headers();
    for (const name of ['content-type', 'cookie', 'origin']) {
      const value = request.headers[name];
      if (typeof value === 'string') headers.set(name, value);
    }

    const upstreamQuery = new URLSearchParams(incoming.searchParams);
    upstreamQuery.delete('__api_path');
    const upstreamUrl = new URL(apiPath, upstreamOrigin);
    upstreamUrl.search = upstreamQuery.toString();
    const upstream = await fetch(upstreamUrl, {
      method,
      headers,
      body: method === 'POST' ? body : undefined,
    });
    response.statusCode = upstream.status;
    upstream.headers.forEach((value, name) => {
      if (name !== 'set-cookie' && name !== 'content-encoding' && name !== 'transfer-encoding') {
        response.setHeader(name, value);
      }
    });
    const cookies = upstream.headers.getSetCookie();
    if (cookies.length) response.setHeader('Set-Cookie', cookies);
    response.end(new Uint8Array(await upstream.arrayBuffer()));
  } catch {
    response.statusCode = 502;
    response.end('The game API is temporarily unavailable.');
  }
}
