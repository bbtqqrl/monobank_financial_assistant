import { fetch as streamingFetch } from 'expo/fetch';
import { z } from 'zod';

import { getTokens, setTokens } from './tokens';

const BASE_URL = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '');

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

// the server answered, but not in the shape the app expects
export class ContractError extends Error {}

export const TokenResponse = z.object({ access_token: z.string(), refresh_token: z.string() });

type Options = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  // false for login/register, which don't send the access token
  auth?: boolean;
};

// RN's fetch never times out on its own
const TIMEOUT_MS = 15_000;

async function send(path: string, { method = 'GET', body, auth = true }: Options, access?: string) {
  if (!BASE_URL) throw new Error('EXPO_PUBLIC_API_URL is not set, see mobile/README.md');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    return await fetch(BASE_URL + path, {
      method,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined && { 'Content-Type': 'application/json' }),
        ...(auth && access && { Authorization: `Bearer ${access}` }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } finally {
    clearTimeout(timer);
  }
}

// FastAPI puts the reason into `detail`, a string or a list of validation errors
async function errorMessage(res: { status: number; json(): Promise<unknown> }) {
  try {
    const data = (await res.json()) as { detail?: unknown } | null;
    const detail = data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  } catch {
    // not JSON
  }
  return `HTTP ${res.status}`;
}

function parse<S extends z.ZodType>(schema: S, data: unknown, path: string): z.infer<S> {
  const result = schema.safeParse(data);
  if (result.success) return result.data;
  const issue = result.error.issues[0];
  throw new ContractError(`${path}: ${issue?.path.join('.') || 'response'} — ${issue?.message}`);
}

export async function saveTokens(res: z.infer<typeof TokenResponse>) {
  await setTokens({ access: res.access_token, refresh: res.refresh_token });
}

// Access tokens live 15 minutes. Parallel requests that hit 401 share one refresh.
let refreshing: Promise<boolean> | null = null;

async function refresh(): Promise<boolean> {
  const tokens = getTokens();
  if (!tokens) return false;
  const res = await send('/auth/refresh', { method: 'POST', body: { refresh_token: tokens.refresh }, auth: false });
  // signed out or signed in again while this was in flight
  const stale = () => getTokens()?.refresh !== tokens.refresh;
  if (stale()) return false;
  if (!res.ok) {
    if (res.status === 401) await setTokens(null);
    return false;
  }
  const next = parse(TokenResponse, await res.json(), '/auth/refresh');
  // reading the body is async too
  if (stale()) return false;
  await saveTokens(next);
  return true;
}

// Sends with the current access token; on 401 refreshes once and sends again.
async function authorized<R extends { status: number }>(
  options: Options,
  go: (access?: string) => Promise<R>,
): Promise<R> {
  const used = getTokens()?.access;
  const res = await go(used);
  if (res.status !== 401 || options.auth === false) return res;

  // another request may have refreshed already while this one was waiting
  const current = getTokens();
  const fresh = !!current && current.access !== used;
  if (!fresh) {
    refreshing ??= refresh().finally(() => {
      refreshing = null;
    });
  }
  return fresh || (await refreshing) ? go(getTokens()?.access) : res;
}

// For calls whose response body isn't used (logout and the like).
export async function request(path: string, options: Options = {}): Promise<unknown> {
  const res = await authorized(options, (access) => send(path, options, access));

  if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
  if (res.status === 204) return undefined;
  try {
    return await res.json();
  } catch {
    // e.g. a Wi-Fi login page instead of the API
    throw new ContractError(`${path}: response is not JSON`);
  }
}

// Every response the app reads goes through a schema, so a changed field on
// the backend shows up here by name instead of as NaN somewhere in the UI.
export async function api<S extends z.ZodType>(schema: S, path: string, options: Options = {}): Promise<z.infer<S>> {
  return parse(schema, await request(path, options), path);
}

// A POST whose answer comes in pieces (server-sent events). RN's own fetch
// hands over the body only once it's complete, expo's reads it as it arrives.
// No timeout: the server stops a reply itself, the caller can abort.
export async function openStream(path: string, body: unknown, signal: AbortSignal) {
  if (!BASE_URL) throw new Error('EXPO_PUBLIC_API_URL is not set, see mobile/README.md');
  const res = await authorized({}, (access) =>
    streamingFetch(BASE_URL + path, {
      method: 'POST',
      signal,
      headers: {
        Accept: 'text/event-stream',
        'Content-Type': 'application/json',
        ...(access && { Authorization: `Bearer ${access}` }),
      },
      body: JSON.stringify(body),
    }),
  );
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
  if (!res.body) throw new ContractError(`${path}: empty response`);
  return res.body;
}
