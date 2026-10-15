import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { CategoryBriefSchema } from './categories';
import { api, request } from './client';

const int = z.number().int();

// GET /budgets, same fields as the backend's BudgetResponse
const BudgetSchema = z.object({
  id: int,
  category: CategoryBriefSchema,
  // monthly limit, kopiyky
  amount: int,
  // spent in the category this month, net of refunds, in hryvnia kopiyky
  current_amount: int,
  // first day of the month the spending is counted for, 'YYYY-MM-DD'
  period_start: z.string(),
});

export type Budget = z.infer<typeof BudgetSchema>;

const KEY = ['budgets'];

export function useBudgets() {
  return useQuery({ queryKey: KEY, queryFn: () => api(z.array(BudgetSchema), '/budgets') });
}

export function useBudget(id: number | undefined) {
  const budgets = useBudgets();
  return budgets.data?.find((b) => b.id === id);
}

export function useSaveBudget() {
  const qc = useQueryClient();
  return useMutation({
    // a new one by category, or a new limit for an existing one
    mutationFn: (budget: { id?: number; categoryId: number; amount: number }) =>
      budget.id === undefined
        ? api(BudgetSchema, '/budgets', { method: 'POST', body: { category_id: budget.categoryId, amount: budget.amount } })
        : api(BudgetSchema, `/budgets/${budget.id}`, { method: 'PATCH', body: { amount: budget.amount } }),
    onSettled: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteBudget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => request(`/budgets/${id}`, { method: 'DELETE' }),
    onSettled: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

// how far into the limit: 0.5 is half spent, above 1 is over it
export const budgetRatio = (b: Budget) => (b.amount > 0 ? b.current_amount / b.amount : 0);
