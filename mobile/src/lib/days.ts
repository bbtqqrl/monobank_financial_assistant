import { txCurrency, type Transaction } from '@/api/transactions';
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

// a sum only makes sense in one currency, so it takes the hryvnia part
export function uahSum(items: Transaction[], currencies: Map<number, number>) {
  return items.filter((t) => txCurrency(t, currencies) === UAH).reduce((acc, t) => acc + t.amount, 0);
}

// hidden when zero, e.g. a transfer out and back on the same day
export function dayTotal(items: Transaction[], currencies: Map<number, number>) {
  const sum = uahSum(items, currencies);
  return sum === 0 ? undefined : formatMoney(sum, UAH, { cents: false });
}
