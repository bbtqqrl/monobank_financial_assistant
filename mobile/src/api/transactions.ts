import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type InfiniteData,
  type QueryClient,
} from '@tanstack/react-query';
import { useMemo } from 'react';
import { z } from 'zod';

import { UAH } from '@/lib/money';
import { isoDate, parseIso, type MonthKey } from '@/lib/period';

import { CategoryBriefSchema, type CategoryBrief } from './categories';
import { api, request } from './client';

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
  category: CategoryBriefSchema.nullable(),
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
export type TxPage = z.infer<typeof PageSchema>;
type Page = TxPage;

export type TxType = 'expense' | 'income' | 'transfer';

export type TxFilters = {
  type?: TxType;
  // matched against the description on the backend
  search?: string;
  // 'YYYY-MM-DD', inclusive, in the phone's time zone
  from?: string;
  to?: string;
  category?: number;
};

function shiftDay(day: string, by: number) {
  const d = parseIso(day);
  return isoDate(new Date(d.getFullYear(), d.getMonth(), d.getDate() + by));
}

// The backend reads from/to as Kyiv days, so it's asked for a day more on
// each side and the edges are cut here by the phone's own clock.
function listUrl({ type, search, from, to, category }: TxFilters, limit: number, page = 1) {
  const params = new URLSearchParams({ limit: String(limit), page: String(page) });
  if (type) params.set('type', type);
  if (search) params.set('search', search);
  if (category !== undefined) params.set('category_id', String(category));
  if (from) params.set('from', shiftDay(from, -1));
  if (to) params.set('to', shiftDay(to, 1));
  return `/transactions?${params}`;
}

function inRange(t: Transaction, { from, to }: TxFilters) {
  const ms = t.time * 1000;
  if (from && ms < parseIso(from).getTime()) return false;
  if (to && ms >= parseIso(shiftDay(to, 1)).getTime()) return false;
  return true;
}

// first page only, for short lists like "Останні транзакції"
export function useTransactions({ type, limit = 30 }: { type?: TxType; limit?: number } = {}) {
  return useQuery({
    queryKey: ['transactions', { type, limit }],
    queryFn: () => api(PageSchema, listUrl({ type }, limit)),
    select: (page) => page.items,
  });
}

// the backend allows up to 100
const PAGE_SIZE = 100;

// the full list, loaded page by page while scrolling
export function useTransactionPages(filters: TxFilters, enabled = true) {
  return useInfiniteQuery({
    queryKey: ['transactions', 'pages', filters],
    enabled,
    queryFn: ({ pageParam }) => api(PageSchema, listUrl(filters, PAGE_SIZE, pageParam)),
    initialPageParam: 1,
    getNextPageParam: (last) => (last.page * last.limit < last.total ? last.page + 1 : undefined),
    select: (data) =>
      filters.from || filters.to
        ? { ...data, pages: data.pages.map((p) => ({ ...p, items: p.items.filter((t) => inRange(t, filters)) })) }
        : data,
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

// lists and sums a new or re-categorised transaction can show up in
const AFFECTED = new Set(['transactions', 'tx-all', 'month-spend', 'tx-active-months', 'tx-oldest']);

const refreshLists = (qc: QueryClient) =>
  qc.invalidateQueries({ predicate: (q) => AFFECTED.has(String(q.queryKey[0])) });

// POST /transactions: money the bank doesn't know about, like cash
export type NewTransaction = {
  description: string;
  // minor units, negative = spent
  amount: number;
  currency_code: number;
  category_id: number;
  // null for cash
  account_id: number | null;
  // unix seconds
  time: number;
};

export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (tx: NewTransaction) => api(TransactionDetailSchema, '/transactions', { method: 'POST', body: tx }),
    onSuccess: (detail) => qc.setQueryData(['transaction', detail.id], detail),
    onSettled: () => refreshLists(qc),
  });
}

// PATCH /transactions/{id}/category. The backend also remembers the choice for
// the merchant (when there's an MCC), so later purchases there follow it.
export function useSetCategory(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (category: CategoryBrief) =>
      api(TransactionDetailSchema, `/transactions/${id}/category`, {
        method: 'PATCH',
        body: { category_id: category.id },
      }),
    // the details screen under the sheet changes right away
    onMutate: async (category) => {
      await qc.cancelQueries({ queryKey: ['transaction', id] });
      const before = qc.getQueryData<TransactionDetail>(['transaction', id]);
      if (before) {
        qc.setQueryData<TransactionDetail>(['transaction', id], {
          ...before,
          category,
          category_source: 'user',
          category_confidence: null,
        });
      }
      return { before };
    },
    onError: (_error, _category, context) => {
      if (context?.before) qc.setQueryData(['transaction', id], context.before);
    },
    onSuccess: (detail) => qc.setQueryData(['transaction', id], detail),
    onSettled: () => refreshLists(qc),
  });
}

// DELETE /transactions/{id}, only for ones added by hand
export function useDeleteTransaction(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => request(`/transactions/${id}`, { method: 'DELETE' }),
    onSettled: () => refreshLists(qc),
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


export function useMonthSpend() {
  const now = new Date();
  const filters: TxFilters = { type: 'expense', from: isoDate(new Date(now.getFullYear(), now.getMonth(), 1)) };
  return useQuery({
    queryKey: ['month-spend', filters.from],
    queryFn: async () => {
      const spent = new Map<number, number>();
      const seen = new Set<number>();
      for (let page = 1; ; page++) {
        const p = await api(PageSchema, listUrl(filters, 100, page));
        for (const t of p.items) {
          // a move between own accounts isn't spending, whatever its category
          if (t.account_id === null || t.transfer_pair_id !== null || seen.has(t.id) || !inRange(t, filters)) continue;
          seen.add(t.id);
          spent.set(t.account_id, (spent.get(t.account_id) ?? 0) - t.amount);
        }
        if (page * p.limit >= p.total) return spent;
      }
    },
  });
}

const MAX_SUM_PAGES = 20;

// Every transaction matching the filters, for period sums under the list.
// Kept out of the 'transactions' key like the month spend. Stops at 2000.
export function useAllTransactions(filters: TxFilters, enabled = true) {
  return useQuery({
    queryKey: ['tx-all', filters],
    enabled,
    queryFn: async () => {
      const byId = new Map<number, Transaction>();
      for (let page = 1; page <= MAX_SUM_PAGES; page++) {
        const p = await api(PageSchema, listUrl(filters, 100, page));
        for (const t of p.items) if (inRange(t, filters)) byId.set(t.id, t);
        if (page * p.limit >= p.total) break;
      }
      return [...byId.values()];
    },
  });
}

// The month of the oldest transaction, so the month strip knows where to start.
// Two small requests: the first page tells the total, the last one the date.
export function useOldestMonth(category?: number) {
  return useQuery({
    queryKey: ['tx-oldest', category],
    queryFn: async () => {
      const first = await api(PageSchema, listUrl({ category }, 1));
      if (first.total === 0) return null;
      const last = await api(PageSchema, listUrl({ category }, 1, first.total));
      const t = last.items[0] ?? first.items[0];
      if (!t) return null;
      const d = new Date(t.time * 1000);
      return { year: d.getFullYear(), month: d.getMonth() };
    },
  });
}

const monthId = (m: MonthKey) => `${m.year}-${m.month}`;

// Which of these months have any transactions, so empty ones can't be picked.
// One small request per month; the backend has no per-month summary yet.
export function useActiveMonths(months: MonthKey[], category?: number) {
  return useQuery({
    queryKey: ['tx-active-months', months.map(monthId), category],
    enabled: months.length > 0,
    queryFn: async () => {
      const found = await Promise.all(
        months.map(async (m) => {
          const range = {
            from: isoDate(new Date(m.year, m.month, 1)),
            to: isoDate(new Date(m.year, m.month + 1, 0)),
            category,
          };
          // the request is a day wider on each side, a neighbour's edge day fits in 100
          const p = await api(PageSchema, listUrl(range, 100));
          return p.items.some((t) => inRange(t, range)) ? monthId(m) : null;
        }),
      );
      return new Set(found.filter((id): id is string => id !== null));
    },
    select: (ids) => (m: MonthKey) => ids.has(monthId(m)),
  });
}

const order = (m: MonthKey) => m.year * 12 + m.month;

// every month from the first transaction up to now, oldest first
function monthsFrom(start: MonthKey): MonthKey[] {
  const now = new Date();
  const out: MonthKey[] = [];
  for (let d = new Date(start.year, start.month, 1); d <= now; d = new Date(d.getFullYear(), d.getMonth() + 1, 1)) {
    out.push({ year: d.getFullYear(), month: d.getMonth() });
  }
  return out;
}

// The months to offer for picking, and which of them have anything in them.
// `loaded` is the oldest month already on screen, in case history grew since.
export function useFeedMonths(loaded?: MonthKey, category?: number) {
  const oldest = useOldestMonth(category);
  const now = new Date();
  const candidates = [oldest.data, loaded].filter((m): m is MonthKey => !!m);
  const start = candidates.reduce<MonthKey>((a, b) => (order(b) < order(a) ? b : a), {
    year: now.getFullYear(),
    month: now.getMonth(),
  });
  const startId = `${start.year}-${start.month}`;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const months = useMemo(() => monthsFrom(start), [startId]);
  const active = useActiveMonths(months, category);
  const isEnabled = (m: MonthKey) =>
    // this month is always there; the rest once known
    (m.year === now.getFullYear() && m.month === now.getMonth()) || (active.data?.(m) ?? true);
  return { months, isEnabled };
}
