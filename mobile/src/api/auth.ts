import { useQuery } from '@tanstack/react-query';
import { useSyncExternalStore } from 'react';
import { z } from 'zod';

import { api, request, saveTokens, TokenResponse } from './client';
import { queryClient } from './query';
import { getTokens, setTokens, subscribeTokens } from './tokens';

export type Session = 'loading' | 'signedIn' | 'signedOut';

// also covers a session that expired on its own, not only the logout button
subscribeTokens(() => {
  if (getTokens() === null) queryClient.clear();
});

export function useSession(): Session {
  const tokens = useSyncExternalStore(subscribeTokens, getTokens);
  if (tokens === undefined) return 'loading';
  return tokens ? 'signedIn' : 'signedOut';
}

// GET /auth/me, the backend's UserResponse
const MeSchema = z.object({
  id: z.number().int(),
  email: z.string(),
  // set once a monobank token is connected
  mono_client_id: z.string().nullable(),
});

export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: () => api(MeSchema, '/auth/me'), staleTime: 5 * 60_000 });
}

export async function signIn(email: string, password: string) {
  const tokens = await api(TokenResponse, '/auth/login', { method: 'POST', body: { email, password }, auth: false });
  queryClient.clear();
  await saveTokens(tokens);
}

// password: 8–128 characters, checked by the backend
export async function register(email: string, password: string) {
  const tokens = await api(TokenResponse, '/auth/register', { method: 'POST', body: { email, password }, auth: false });
  queryClient.clear();
  await saveTokens(tokens);
}

// local first, the server revoke is best effort
export async function signOut() {
  const refresh = getTokens()?.refresh;
  await setTokens(null).catch(() => {});
  if (refresh) {
    request('/auth/logout', { method: 'POST', body: { refresh_token: refresh }, auth: false }).catch(() => {});
  }
}
