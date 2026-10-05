import { useInfiniteQuery, useQuery, useQueryClient, type InfiniteData, type QueryClient } from '@tanstack/react-query';

import { UAH } from '@/lib/money';

import { api } from './client';

// GET /transactions, same fields as the backend's TransactionListItem
export type Transaction = {
  id: number;
  source: 'monobank' | 'manual' | string;
  // unix seconds
  time: number;
  description: string;
  // minor units in the account's currency, negative = spent
  amount: number;
  // minor units in the currency of the purchase itself
  operation_amount: number | null;
  currency_code: number;
  mcc: number | null;
  account_id: number | null;
  jar_id: number | null;
  transfer_pair_id: number | null;
  category: { id: number; name: string; slug: string } | null;
  // ai, ai_low_confidence, mapping, mapping_low_confidence, rule, user, ai_failed
  category_source: string | null;
  category_confidence: number | null;
};

// GET /transactions/{id}
export type TransactionDetail = Transaction & {
  // account balance right after this transaction
  balance: number | null;
  comment: string | null;
  counter_name: string | null;
  counter_edrpou: string | null;
  counter_iban: string | null;
};

export type TxType = 'expense' | 'income' | 'transfer';

type Page = { items: Transaction[]; page: number; limit: number; total: number };

function listUrl(type: TxType | undefined, limit: number, page = 1) {
  const params = new URLSearchParams({ limit: String(limit), page: String(page) });
  if (type) params.set('type', type);
  return `/transactions?${params}`;
}

// first page only, for short lists like "Останні транзакції"
export function useTransactions({ type, limit = 30 }: { type?: TxType; limit?: number } = {}) {
  return useQuery({
    queryKey: ['transactions', { type, limit }],
    queryFn: () => api<Page>(listUrl(type, limit)),
    select: (page) => page.items,
  });
}

const PAGE_SIZE = 50;

// the full list, loaded page by page while scrolling
export function useTransactionPages(type?: TxType) {
  return useInfiniteQuery({
    queryKey: ['transactions', 'pages', { type }],
    queryFn: ({ pageParam }) => api<Page>(listUrl(type, PAGE_SIZE, pageParam)),
    initialPageParam: 1,
    getNextPageParam: (last) => (last.page * last.limit < last.total ? last.page + 1 : undefined),
  });
}

// The list already has most fields, so the screen can draw right away and
// fill in balance, comment and the counterparty when the request comes back.
function fromLists(qc: QueryClient, id: number): TransactionDetail | undefined {
  for (const [, data] of qc.getQueriesData<Page | InfiniteData<Page>>({ queryKey: ['transactions'] })) {
    const pages = !data ? [] : 'pages' in data ? data.pages : [data];
    const item = pages.flatMap((p) => p.items).find((t) => t.id === id);
    if (item) {
      return { ...item, balance: null, comment: null, counter_name: null, counter_edrpou: null, counter_iban: null };
    }
  }
  return undefined;
}

export function useTransaction(id: number) {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ['transaction', id],
    queryFn: () => api<TransactionDetail>(`/transactions/${id}`),
    placeholderData: () => fromLists(qc, id),
    enabled: Number.isInteger(id),
  });
}

// `amount` is in the account's currency, `currency_code` is the purchase's own
export function txCurrency(t: Transaction, accountCurrency: Map<number, number>): number {
  return t.account_id !== null ? (accountCurrency.get(t.account_id) ?? UAH) : t.currency_code;
}

// the purchase in its own currency when that differs from the account's
export function foreignPart(t: Transaction, accountCurrency: Map<number, number>) {
  if (t.operation_amount === null || t.currency_code === txCurrency(t, accountCurrency)) return undefined;
  return { amount: t.operation_amount, currency: t.currency_code };
}
