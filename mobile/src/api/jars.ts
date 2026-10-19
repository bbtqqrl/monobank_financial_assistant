import { z } from 'zod';

// same fields as the backend's JarResponse
export const JarSchema = z.object({
  id: z.number().int(),
  mono_jar_id: z.string(),
  title: z.string(),
  description: z.string().nullable(),
  currency_code: z.number().int(),
  // minor units
  balance: z.number().int(),
  goal: z.number().int().nullable(),
  is_active: z.boolean(),
});

export type Jar = z.infer<typeof JarSchema>;

export const JARS_KEY = ['jars'];

// the share of the goal saved, 0..1; null for a jar without a goal
export function jarProgress(jar: Jar): number | null {
  if (!jar.goal || jar.goal <= 0) return null;
  return Math.min(1, Math.max(0, jar.balance / jar.goal));
}

const DAY_MS = 86_400_000;
// the pace is taken from this many recent days
const PACE_DAYS = 90;
// a young jar is measured from its first deposit, but over two weeks at least
const MIN_PACE_DAYS = 14;
// further than this is no date worth showing
const MAX_AHEAD_DAYS = 5 * 365;

// When the goal is reached if money keeps coming in as it did lately. Null
// without a goal, once it's reached, or when the jar isn't growing.
export function jarGoalDate(jar: Jar, items: { time: number; amount: number }[], now = Date.now()): Date | null {
  if (!jar.goal || jar.balance >= jar.goal) return null;
  const recent = items.filter((t) => t.time * 1000 >= now - PACE_DAYS * DAY_MS);
  if (!recent.length) return null;
  const oldest = Math.min(...recent.map((t) => t.time * 1000));
  const days = Math.max(MIN_PACE_DAYS, (now - oldest) / DAY_MS);
  const perDay = recent.reduce((sum, t) => sum + t.amount, 0) / days;
  if (perDay <= 0) return null;
  const ahead = (jar.goal - jar.balance) / perDay;
  return ahead > MAX_AHEAD_DAYS ? null : new Date(now + ahead * DAY_MS);
}
