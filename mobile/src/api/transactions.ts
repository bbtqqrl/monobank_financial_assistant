import { useInfiniteQuery, useQuery, useQueryClient, type InfiniteData, type QueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { UAH } from '@/lib/money';

import { api } from './client';

const int = z.number().int();

// GET /transactions, same fields as the backend's TransactionListItem
const TransactionSchema = z.object({
  id: int,
  // monobank or manual
  source: z.string(),
  // unix seconds
  time: int,
  description: z.string(),
  // minor units in the account's currency, negative = spent
  amount: int,
  // minor units in the currency of the purchase itself
  operation_amount: int.nullable(),
  currency_code: int,
  mcc: int.nullable(),
  account_id: int.nullable(),
  jar_id: int.nullable(),
  transfer_pair_id: int.nullable(),
  category: z.object({ id: int, name: z.string(), slug: z.string() }).nullable(),
  // ai, ai_low_confidence, mapping, mapping_low_confidence, rule, user, ai_failed
  category_source: z.string().nullable(),
  category_confidence: z.number().nullable(),
});

// GET /transactions/{id}
const TransactionDetailSchema = TransactionSchema.extend({
  // account balance right after this transaction
  balance: int.nullable(),
  comment: z.string().nullable(),
  counter_name: z.string().nullable(),
  counter_edrpou: z.string().nullable(),
  counter_iban: z.string().nullable(),
});

const PageSchema = z.object({ items: z.array(TransactionSchema), page: int, limit: int, total: int });

export type Transaction = z.infer<typeof TransactionSchema>;
export type TransactionDetail = z.infer<typeof TransactionDetailSchema>;
type Page = z.infer<typeof PageSchema>;

export type TxType = 'expense' | 'income' | 'transfer';

function listUrl(type: TxType | undefined, limit: number, page = 1) {
  const params = new URLSearchParams({ limit: String(limit), page: String(page) });
  if (type) params.set('type', type);
  return `/transactions?${params}`;
}

// first page only, for short lists like "Останні транзакції"
export function useTransactions({ type, limit = 30 }: { type?: TxType; limit?: number } = {}) {
  return useQuery({
    queryKey: ['transactions', { type, limit }],
    queryFn: () => api(PageSchema, listUrl(type, limit)),
    select: (page) => page.items,
  });
}

const PAGE_SIZE = 50;

// the full list, loaded page by page while scrolling
export function useTransactionPages(type?: TxType) {
  return useInfiniteQuery({
    queryKey: ['transactions', 'pages', { type }],
    queryFn: ({ pageParam }) => api(PageSchema, listUrl(type, PAGE_SIZE, pageParam)),
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
    queryFn: () => api(TransactionDetailSchema, `/transactions/${id}`),
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

function monthStart(now: Date) {
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  return `${now.getFullYear()}-${mm}-01`;
}

export function useMonthSpend() {
  const from = monthStart(new Date());
  return useQuery({
    queryKey: ['month-spend', from],
    queryFn: async () => {
      const spent = new Map<number, number>();
      const seen = new Set<number>();
      for (let page = 1; ; page++) {
        const p = await api(PageSchema, `/transactions?type=expense&from=${from}&limit=100&page=${page}`);
        for (const t of p.items) {
          if (t.account_id === null || seen.has(t.id)) continue;
          seen.add(t.id);
          spent.set(t.account_id, (spent.get(t.account_id) ?? 0) - t.amount);
        }
        if (page * p.limit >= p.total) return spent;
      }
    },
  });
}
