import type { CategoryBrief, CategoryKind } from '@/api/categories';
import { createStore } from '@/lib/store';

export type DraftDirection = 'expense' | 'income';

export const DRAFT_KINDS: Record<DraftDirection, readonly CategoryKind[]> = {
  expense: ['expense', 'transfer'],
  income: ['income', 'transfer'],
};

export const QUICK_SLUGS: Record<DraftDirection, readonly string[]> = {
  expense: [
    'produkty',
    'kafe-ta-restorany',
    'transport',
    'taksi',
    'rozvahy',
    'zdorovia',
    'odiah',
    'komunalni-posluhy',
    'podarunky-ta-blahodiinist',
  ],
  income: ['zarplata', 'perekazy-vid-liudei', 'pidpryiemnytstvo', 'keshbek', 'prodazh-rechei', 'inshi-dokhody'],
};

// the category picked for a new transaction; its own sheet writes here
export const draftCategory = createStore<CategoryBrief | null>(null);
