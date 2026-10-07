import { useSyncExternalStore } from 'react';

// A tiny shared value for screens that can't pass state to each other
// directly, like a sheet route and the screen under it.
export function createStore<T>(initial: T) {
  let value = initial;
  const listeners = new Set<() => void>();
  const subscribe = (listener: () => void) => {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  };

  return {
    get: () => value,
    set: (next: T) => {
      value = next;
      listeners.forEach((l) => l());
    },
    subscribe,
    useValue: () => useSyncExternalStore(subscribe, () => value),
  };
}
