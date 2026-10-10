import type { Transaction } from '@/api/transactions';
import { periodFlow } from '@/lib/flow';
import { formatMoney, UAH } from '@/lib/money';
import { dayKey, dayLabel } from '@/lib/time';

export type Day = { key: string; label: string; items: Transaction[] };

// Pages come newest first, so a day's transactions are always next to each other.
// Offset pages overlap when a new transaction lands between fetches.
export function byDay(items: Transaction[]): Day[] {
  const days: Day[] = [];
  const seen = new Set<number>();
  for (const t of items) {
    if (seen.has(t.id)) continue;
    seen.add(t.id);
    const key = dayKey(t.time);
    const last = days[days.length - 1];
    if (last?.key === key) last.items.push(t);
    else days.push({ key, label: dayLabel(t.time), items: [t] });
  }
  return days;
}

// Money in minus money out, counted like the month summary: the user's own
// money moving between cards, jars and cash is left out. Hidden when zero.
export function dayTotal(items: Transaction[], currencies: Map<number, number>) {
  const { spent, income } = periodFlow(items, currencies);
  const sum = income + spent;
  return sum === 0 ? undefined : formatMoney(sum, UAH, { cents: false, sign: 'always' });
}
