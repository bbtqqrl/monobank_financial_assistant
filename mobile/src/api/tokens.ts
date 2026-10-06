import * as SecureStore from 'expo-secure-store';
import { z } from 'zod';

// JWT pair from the backend, kept in the Keychain between launches.
const TokensSchema = z.object({ access: z.string(), refresh: z.string() });
export type Tokens = z.infer<typeof TokensSchema>;

const KEY = 'auth.tokens';

// undefined until read from the Keychain, null when signed out
let current: Tokens | null | undefined;
const listeners = new Set<() => void>();

export function getTokens(): Tokens | null | undefined {
  return current;
}

export function subscribeTokens(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export async function loadTokens() {
  if (current !== undefined) return;
  let stored: Tokens | null = null;
  try {
    const raw = await SecureStore.getItemAsync(KEY);
    stored = raw ? TokensSchema.parse(JSON.parse(raw)) : null;
  } catch {
    // unreadable entry, treat as signed out
  }
  current = stored;
  listeners.forEach((l) => l());
}

export async function setTokens(tokens: Tokens | null) {
  current = tokens;
  listeners.forEach((l) => l());
  if (tokens) await SecureStore.setItemAsync(KEY, JSON.stringify(tokens));
  else await SecureStore.deleteItemAsync(KEY);
}
