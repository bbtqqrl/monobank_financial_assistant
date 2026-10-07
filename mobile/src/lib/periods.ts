import type { Period } from '@/lib/period';
import { createStore } from '@/lib/store';

// What the transactions list and the search show; the period sheet writes here.
// The list is one long feed ('all') unless a custom range is picked.
export const listPeriod = createStore<Period>({ kind: 'all' });
// a month picked in the sheet for the list to scroll to
export const listJump = createStore<{ year: number; month: number } | null>(null);
export const searchPeriod = createStore<Period>({ kind: 'all' });

export type PeriodTarget = 'list' | 'search';

export function periodStore(target: PeriodTarget) {
  return target === 'list' ? listPeriod : searchPeriod;
}
