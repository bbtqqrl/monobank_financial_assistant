import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import type { MonthKey } from '@/lib/period';

import { api } from './client';

const int = z.number().int();

// all sums are spending in hryvnia kopiyky, positive
const PeriodSchema = z.object({ start: z.string(), end: z.string(), days: int });

const ComparisonSchema = z.object({
  type: z.string(),
  start: z.string(),
  end: z.string(),
  days: int,
  scaled: z.boolean(),
  // the comparison period has history behind it from start to end
  complete: z.boolean(),
  total: int,
  // what the period would have cost at the comparison's pace
  expected: int,
});

const SpendingSchema = z.object({
  period: PeriodSchema,
  total: int,
  comparison: ComparisonSchema,
  // against comparison.expected; null without a baseline
  change_pct: z.number().nullable(),
  // running total per day, from the period's start up to today
  daily: z.array(z.object({ date: z.string(), amount: int })),
});

const CategoryShareSchema = z.object({
  category_id: int,
  name: z.string(),
  slug: z.string(),
  amount: int,
  // percent of the period's total
  share: z.number(),
  transaction_count: int,
  expected: int,
  change_pct: z.number().nullable(),
});

const CategoriesSchema = z.object({
  period: PeriodSchema,
  total: int,
  transaction_count: int,
  comparison: ComparisonSchema,
  items: z.array(CategoryShareSchema),
  // what's left beyond the top ones, when asked for a top
  other: z.object({ amount: int, share: z.number() }).nullable(),
});

const MerchantSchema = z.object({
  merchant_key: z.string(),
  name: z.string(),
  purchase_count: int,
  amount: int,
  // the category most of its purchases are in
  category: z.object({ id: int, name: z.string(), slug: z.string() }).nullable(),
  logo_url: z.string().nullable().optional(),
});

const MerchantsSchema = z.object({
  period: PeriodSchema,
  total: int,
  limit: int,
  offset: int,
  items: z.array(MerchantSchema),
});

export type Spending = z.infer<typeof SpendingSchema>;
export type CategoryShare = z.infer<typeof CategoryShareSchema>;
export type CategoryShares = z.infer<typeof CategoriesSchema>;
export type Merchant = z.infer<typeof MerchantSchema>;

// 'YYYY-MM', what the backend's month= expects
export function monthParam({ year, month }: MonthKey) {
  return `${year}-${String(month + 1).padStart(2, '0')}`;
}

// /analytics/<path> for one month
const query = (path: string, month: MonthKey, extra: Record<string, string> = {}) =>
  `/analytics/${path}?${new URLSearchParams({ month: monthParam(month), ...extra })}`;

// switching months keeps the last one on screen until the new one comes
const common = { placeholderData: keepPreviousData };

export function useSpending(month: MonthKey) {
  return useQuery({
    queryKey: ['analytics', 'spending', monthParam(month)],
    // compared with the same days of the month before
    queryFn: () => api(SpendingSchema, query('spending', month, { compare: 'previous_month' })),
    ...common,
  });
}

export function useCategoryShares(month: MonthKey, top?: number) {
  return useQuery({
    queryKey: ['analytics', 'categories', monthParam(month), top ?? 'all'],
    queryFn: () =>
      api(
        CategoriesSchema,
        query('categories', month, { compare: 'previous_month', ...(top ? { top: String(top) } : {}) }),
      ),
    ...common,
  });
}

export function useTopMerchants(month: MonthKey, limit: number) {
  return useQuery({
    queryKey: ['analytics', 'merchants', monthParam(month), limit],
    queryFn: () => api(MerchantsSchema, query('merchants', month, { limit: String(limit) })),
    ...common,
  });
}
