import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { api } from './client';

const int = z.number().int();

// What a transaction in the category means for the user's money:
//   expense  - spent; a positive amount is a refund
//   income   - received from outside
//   transfer - the user's own money moving (own accounts, jars, cash, loans)
//   unknown  - nothing fits, counted by the amount's sign
// A kind the app doesn't know yet is treated as unknown rather than an error.
const KindSchema = z.enum(['expense', 'income', 'transfer', 'unknown']).catch('unknown');

export type CategoryKind = z.infer<typeof KindSchema>;

export const CategoryBriefSchema = z.object({ id: int, name: z.string(), slug: z.string(), kind: KindSchema });

export type CategoryBrief = z.infer<typeof CategoryBriefSchema>;

// GET /categories: top-level categories with their children, one level deep
const TreeSchema = z.array(CategoryBriefSchema.extend({ children: z.array(CategoryBriefSchema) }));

export type CategoryNode = z.infer<typeof TreeSchema>[number];

const HOUR = 60 * 60 * 1000;

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: () => api(TreeSchema, '/categories'),
    // only changes with a backend release
    staleTime: HOUR,
  });
}
