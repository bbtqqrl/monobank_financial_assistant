import type { QueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { AccountSchema } from './accounts';
import { api, ApiError } from './client';

// The backend re-reads cards and balances from monobank with the stored token.
// Webhooks only bring transactions, so balances go stale without this.
const SYNC_PATH = '/monobank/debug/client-info';

const SyncSchema = z.object({ accounts: z.array(AccountSchema) });

// monobank allows one client-info call a minute per token
const MIN_INTERVAL_MS = 60_000;
let lastSync = 0;

// false when it didn't happen: too soon, rate limited or not connected
async function syncMonobank(qc: QueryClient): Promise<boolean> {
  if (Date.now() - lastSync < MIN_INTERVAL_MS) return false;
  lastSync = Date.now();
  try {
    const { accounts } = await api(SyncSchema, SYNC_PATH, { method: 'POST' });
    qc.setQueryData(['accounts'], accounts);
    return true;
  } catch (e) {
    // anything but the rate limit or a missing token can be tried again right away
    if (!(e instanceof ApiError && (e.status === 429 || e.status === 400))) lastSync = 0;
    return false;
  }
}

// Pull-to-refresh: balances straight from monobank, or the stored ones when
// that can't happen right now
export async function refreshAccounts(qc: QueryClient) {
  if (await syncMonobank(qc)) return;
  await qc.refetchQueries({ queryKey: ['accounts'], exact: true });
}
