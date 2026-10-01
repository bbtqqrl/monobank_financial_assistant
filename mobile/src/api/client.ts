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

type TokenResponse = { access_token: string; refresh_token: string };

type Options = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  // false for login/register, which don't send the access token
  auth?: boolean;
};

async function send(path: string, { method = 'GET', body, auth = true }: Options) {
  if (!BASE_URL) throw new Error('EXPO_PUBLIC_API_URL is not set, see mobile/README.md');
  const access = auth ? getTokens()?.access : undefined;
  return fetch(BASE_URL + path, {
    method,
    headers: {
      Accept: 'application/json',
      ...(body !== undefined && { 'Content-Type': 'application/json' }),
      ...(access && { Authorization: `Bearer ${access}` }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

// FastAPI puts the reason into `detail`, a string or a list of validation errors
async function errorMessage(res: Response) {
  try {
    const data = await res.json();
    if (typeof data?.detail === 'string') return data.detail;
    if (Array.isArray(data?.detail) && data.detail[0]?.msg) return String(data.detail[0].msg);
  } catch {
    // not JSON
  }
  return `HTTP ${res.status}`;
}

export async function saveTokens(res: TokenResponse) {
  await setTokens({ access: res.access_token, refresh: res.refresh_token });
}

// Access tokens live 15 minutes. Parallel requests that hit 401 share one refresh.
let refreshing: Promise<boolean> | null = null;

async function refresh(): Promise<boolean> {
  const tokens = getTokens();
  if (!tokens) return false;
  const res = await send('/auth/refresh', { method: 'POST', body: { refresh_token: tokens.refresh }, auth: false });
  if (!res.ok) {
    // refresh token expired or revoked: back to the login screen
    if (res.status === 401) await setTokens(null);
    return false;
  }
  await saveTokens(await res.json());
  return true;
}

export async function api<T>(path: string, options: Options = {}): Promise<T> {
  let res = await send(path, options);

  if (res.status === 401 && options.auth !== false) {
    refreshing ??= refresh().finally(() => {
      refreshing = null;
    });
    if (await refreshing) res = await send(path, options);
  }

  if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
