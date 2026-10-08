import type { CategoryBrief } from '@/api/categories';
import { createStore } from '@/lib/store';

// the category the transactions list is narrowed to; the category sheet writes here
export const listCategory = createStore<CategoryBrief | null>(null);
