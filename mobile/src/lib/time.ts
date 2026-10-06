// All in the device time zone.

const DAY_MS = 24 * 60 * 60 * 1000;

const clock = new Intl.DateTimeFormat('uk', { hour: '2-digit', minute: '2-digit' });
const dayMonth = new Intl.DateTimeFormat('uk', { day: 'numeric', month: 'long' });
const dayMonthYear = new Intl.DateTimeFormat('uk', { day: 'numeric', month: 'long', year: 'numeric' });

function startOfDay(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

function daysAgo(d: Date, now: Date) {
  // round, not floor: a DST day is 23 or 25 hours long
  return Math.round((startOfDay(now) - startOfDay(d)) / DAY_MS);
}

// uk adds " р." after the year, the design doesn't
function withYear(d: Date) {
  return dayMonthYear.format(d).replace(/\s*р\.$/, '');
}

function date(d: Date, now: Date) {
  return d.getFullYear() === now.getFullYear() ? dayMonth.format(d) : withYear(d);
}

// "10:32"
export function clockLabel(unixSeconds: number) {
  return clock.format(new Date(unixSeconds * 1000));
}

// Right column of a row in short lists: "10:32" today, "Вчора", "18 травня",
// "18 травня 2025" for older years.
export function whenLabel(unixSeconds: number, now = new Date()) {
  const d = new Date(unixSeconds * 1000);
  const days = daysAgo(d, now);
  if (days === 0) return clock.format(d);
  if (days === 1) return 'Вчора';
  return date(d, now);
}

// Day group header: "Сьогодні", "Вчора", "18 травня"
export function dayLabel(unixSeconds: number, now = new Date()) {
  const d = new Date(unixSeconds * 1000);
  const days = daysAgo(d, now);
  if (days === 0) return 'Сьогодні';
  if (days === 1) return 'Вчора';
  return date(d, now);
}

// groups transactions by local day
export function dayKey(unixSeconds: number) {
  const d = new Date(unixSeconds * 1000);
  return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;
}

// "20 травня 2026, 10:32"
export function fullDate(unixSeconds: number) {
  const d = new Date(unixSeconds * 1000);
  return `${withYear(d)}, ${clock.format(d)}`;
}

// "жовтень"
export function monthLabel(d = new Date()) {
  return new Intl.DateTimeFormat('uk', { month: 'long' }).format(d);
}
