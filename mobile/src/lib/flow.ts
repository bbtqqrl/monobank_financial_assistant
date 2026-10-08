import { txCurrency, type Transaction } from '@/api/transactions';
import { UAH } from '@/lib/money';
import { isoDate, parseIso, type Period } from '@/lib/period';

export type Flow = {
  // minor units, hryvnia part only; spent is negative
  spent: number;
  income: number;
  // 'YYYY-MM-DD' → spent that day, less refunds
  daily: Map<string, number>;
};

// Money in and out for a period, by the category's kind. The user's own money
// moving (own accounts, jars, cash) is neither and is left out; a refund in a
// spending category lowers the spending instead of counting as income.
export function periodFlow(items: Transaction[], currencies: Map<number, number>): Flow {
  const flow: Flow = { spent: 0, income: 0, daily: new Map() };
  for (const t of items) {
    const kind = t.category?.kind ?? 'unknown';
    if (kind === 'transfer' || t.transfer_pair_id !== null || txCurrency(t, currencies) !== UAH) continue;
    if (kind === 'income' || (kind === 'unknown' && t.amount > 0)) {
      flow.income += t.amount;
      continue;
    }
    flow.spent += t.amount;
    const day = isoDate(new Date(t.time * 1000));
    flow.daily.set(day, (flow.daily.get(day) ?? 0) - t.amount);
  }
  return flow;
}

const MAX_BAR_DAYS = 62;

// days to draw bars for: the whole month (future days included, dimmed) or a
// short custom range; nothing for all time
export function periodDays(p: Period): string[] {
  let from: Date;
  let to: Date;
  if (p.kind === 'month') {
    from = new Date(p.year, p.month, 1);
    to = new Date(p.year, p.month + 1, 0);
  } else if (p.kind === 'custom') {
    from = parseIso(p.from);
    to = parseIso(p.to);
  } else {
    return [];
  }
  const days: string[] = [];
  for (let d = from; d <= to && days.length <= MAX_BAR_DAYS; d = new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1)) {
    days.push(isoDate(d));
  }
  return days.length > MAX_BAR_DAYS ? [] : days;
}
