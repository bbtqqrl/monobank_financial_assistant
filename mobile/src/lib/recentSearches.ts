import AsyncStorage from '@react-native-async-storage/async-storage';
import { useSyncExternalStore } from 'react';

const KEY = 'search.recent';
const MAX = 5;

let recent: string[] = [];
let loaded = false;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  if (!loaded) {
    loaded = true;
    AsyncStorage.getItem(KEY)
      .then((raw) => {
        const parsed: unknown = raw ? JSON.parse(raw) : [];
        if (Array.isArray(parsed)) recent = parsed.filter((q): q is string => typeof q === 'string').slice(0, MAX);
        emit();
      })
      .catch(() => {});
  }
  return () => listeners.delete(listener);
}

export function useRecentSearches(): string[] {
  return useSyncExternalStore(subscribe, () => recent);
}

export function addRecentSearch(query: string) {
  const q = query.trim();
  if (!q) return;
  recent = [q, ...recent.filter((r) => r.toLowerCase() !== q.toLowerCase())].slice(0, MAX);
  emit();
  AsyncStorage.setItem(KEY, JSON.stringify(recent)).catch(() => {});
}
