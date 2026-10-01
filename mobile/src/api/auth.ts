import { useSyncExternalStore } from 'react';

import { api, saveTokens } from './client';
import { queryClient } from './query';
import { getTokens, setTokens, subscribeTokens } from './tokens';

type TokenResponse = { access_token: string; refresh_token: string };

export type Session = 'loading' | 'signedIn' | 'signedOut';

export function useSession(): Session {
  const tokens = useSyncExternalStore(subscribeTokens, getTokens);
  if (tokens === undefined) return 'loading';
  return tokens ? 'signedIn' : 'signedOut';
}

export async function signIn(email: string, password: string) {
  await saveTokens(await api<TokenResponse>('/auth/login', { method: 'POST', body: { email, password }, auth: false }));
}

// password: 8–128 characters, checked by the backend
export async function register(email: string, password: string) {
  await saveTokens(
    await api<TokenResponse>('/auth/register', { method: 'POST', body: { email, password }, auth: false }),
  );
}

export async function signOut() {
  const refresh = getTokens()?.refresh;
  // revoke on the server if we can, sign out locally either way
  if (refresh) {
    await api('/auth/logout', { method: 'POST', body: { refresh_token: refresh }, auth: false }).catch(() => {});
  }
  await setTokens(null);
  queryClient.clear();
}
