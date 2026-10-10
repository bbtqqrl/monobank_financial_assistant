import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import type { Flash } from '@/lib/useFlash';

import { AccountSchema } from './accounts';
import { api } from './client';

// The backend re-reads cards and balances from monobank with the stored token.
// Webhooks only bring transactions, so balances go stale without this.
const SYNC_PATH = '/monobank/debug/client-info';

const SyncSchema = z.object({
  accounts: z.array(AccountSchema),
  // false when monobank sends new transactions somewhere else or nowhere
  webhook_registered: z.boolean(),
});

export type MonobankStatus = { live: boolean };

const STATUS_KEY = ['monobank'];
// monobank allows one client-info call a minute per token
const MIN_INTERVAL_MS = 60_000;

const statusQuery = (qc: QueryClient) => ({
  queryKey: STATUS_KEY,
  queryFn: async (): Promise<MonobankStatus> => {
    const data = await api(SyncSchema, SYNC_PATH, { method: 'POST' });
    qc.setQueryData(['accounts'], data.accounts);
    return { live: data.webhook_registered };
  },
  staleTime: MIN_INTERVAL_MS,
  retry: false,
});

// Whether new transactions arrive on their own. Checking it syncs the balances too.
export function useMonobankStatus(enabled: boolean) {
  const qc = useQueryClient();
  return useQuery({ ...statusQuery(qc), enabled });
}

// under a minute since the last sync: monobank would turn another one down
export function syncedRecently(qc: QueryClient) {
  return Date.now() - (qc.getQueryState(STATUS_KEY)?.dataUpdatedAt ?? 0) < MIN_INTERVAL_MS;
}

export type RefreshResult = 'synced' | 'recent' | 'failed';

// what to tell the user after a refresh
export const REFRESH_FLASH: Record<RefreshResult, Flash> = {
  synced: { ok: true, text: 'Оновлено' },
  // synced under a minute ago, there's nothing newer to get
  recent: { ok: true, text: 'Дані вже актуальні' },
  failed: { ok: false, text: 'Не вдалося оновити' },
};

// Pull-to-refresh: balances straight from monobank, or the stored ones when
// that can't happen right now (synced under a minute ago, rate limited, not connected)
export async function refreshAccounts(qc: QueryClient): Promise<RefreshResult> {
  const recent = syncedRecently(qc);
  if (!recent) {
    try {
      await qc.fetchQuery({ ...statusQuery(qc), staleTime: 0 });
      return 'synced';
    } catch {
      // falls back to the stored balances below
    }
  }
  await qc.refetchQueries({ queryKey: ['accounts'], exact: true });
  return recent ? 'recent' : 'failed';
}
