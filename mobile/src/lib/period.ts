export type Period =
  | { kind: 'all' }
  | { kind: 'week' }
  // month is 0-based, like Date
  | { kind: 'month'; year: number; month: number }
  | { kind: 'custom'; from: string; to: string };

// month is 0-based, like Date
export type MonthKey = { year: number; month: number };

const DAY_MS = 24 * 60 * 60 * 1000;

// local 'YYYY-MM-DD', what the backend's from/to expect
export function isoDate(d: Date) {
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mm}-${dd}`;
}

export function parseIso(s: string) {
  const [y = 0, m = 1, d = 1] = s.split('-').map(Number);
  return new Date(y, m - 1, d);
}

export function periodRange(p: Period, now = new Date()): { from?: string; to?: string } {
  switch (p.kind) {
    case 'all':
      return {};
    case 'week': {
      // weeks start on Monday
      const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - ((now.getDay() + 6) % 7));
      return { from: isoDate(monday), to: isoDate(now) };
    }
    case 'month': {
      const last = new Date(p.year, p.month + 1, 0);
      return { from: isoDate(new Date(p.year, p.month, 1)), to: isoDate(last < now ? last : now) };
    }
    case 'custom':
      return { from: p.from, to: p.to };
  }
}

const dayMonth = new Intl.DateTimeFormat('uk', { day: 'numeric', month: 'long' });
const monthNameFmt = new Intl.DateTimeFormat('uk', { month: 'long' });

// "12 – 20 травня", "28 вересня – 3 жовтня", years only when not this year
export function rangeLabel(from: string, to: string, now = new Date()) {
  const a = parseIso(from);
  const b = parseIso(to);
  const year = (d: Date) => (d.getFullYear() === now.getFullYear() ? '' : ` ${d.getFullYear()}`);
  if (from === to) return dayMonth.format(a) + year(a);
  if (a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth()) {
    return `${a.getDate()} – ${dayMonth.format(b)}${year(b)}`;
  }
  return `${dayMonth.format(a)}${a.getFullYear() === b.getFullYear() ? '' : year(a)} – ${dayMonth.format(b)}${year(b)}`;
}

// days in an inclusive range
export function rangeDays(from: string, to: string) {
  return Math.round((parseIso(to).getTime() - parseIso(from).getTime()) / DAY_MS) + 1;
}

export function thisMonth(now = new Date()): Period {
  return { kind: 'month', year: now.getFullYear(), month: now.getMonth() };
}

export function isThisMonth(p: Period, now = new Date()) {
  return p.kind === 'month' && p.year === now.getFullYear() && p.month === now.getMonth();
}

export function shiftMonth(p: Extract<Period, { kind: 'month' }>, by: number): Period {
  const d = new Date(p.year, p.month + by, 1);
  return { kind: 'month', year: d.getFullYear(), month: d.getMonth() };
}

export function periodLabel(p: Period) {
  switch (p.kind) {
    case 'all':
      return 'Увесь час';
    case 'week':
      return 'Цей тиждень';
    case 'month':
      return monthTitle(new Date(p.year, p.month, 1));
    case 'custom':
      return rangeLabel(p.from, p.to);
  }
}

// "Травень"
export function monthName(d: Date) {
  const name = monthNameFmt.format(d);
  return `${name[0]!.toUpperCase()}${name.slice(1)}`;
}

// "Травень 2026"
export function monthTitle(d: Date) {
  return `${monthName(d)} ${d.getFullYear()}`;
}
