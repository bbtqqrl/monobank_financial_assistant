import { useQuery } from '@tanstack/react-query';

import { UAH } from '@/lib/money';

import { api } from './client';

// GET /accounts, same fields as the backend's AccountResponse
export type Account = {
  id: number;
  mono_account_id: string;
  account_type: string;
  currency_code: number;
  balance: number;
  credit_limit: number;
  masked_pan: string | null;
  iban: string | null;
  is_active: boolean;
};

export function useAccounts() {
  return useQuery({ queryKey: ['accounts'], queryFn: () => api<Account[]>('/accounts') });
}

// monobank card types
const CARD_NAMES: Record<string, string> = {
  black: 'Чорна',
  white: 'Біла',
  platinum: 'Platinum',
  iron: 'Iron',
  yellow: 'Жовта',
  fop: 'ФОП',
  eAid: 'єПідтримка',
  madeInUkraine: 'Національний кешбек',
  diia: 'Дія',
};

// currency accounts come as type "black" too, name them by currency instead
const CURRENCY_NAMES: Record<number, string> = {
  840: 'Доларова',
  978: 'Єврова',
  985: 'Злотова',
  826: 'Фунтова',
};

// the black UAH card if there is one, otherwise the first UAH account
export function mainAccount(accounts: Account[]): Account | undefined {
  const active = accounts.filter((a) => a.is_active);
  const uah = active.filter((a) => a.currency_code === UAH);
  return uah.find((a) => a.account_type === 'black') ?? uah[0] ?? active[0];
}

// main account first, then the rest in the bank's order, empty ones at the end
export function sortedAccounts(accounts: Account[]): Account[] {
  const main = mainAccount(accounts);
  const rest = accounts.filter((a) => a.is_active && a !== main);
  const filled = rest.filter((a) => ownBalance(a) !== 0);
  const empty = rest.filter((a) => ownBalance(a) === 0);
  return [...(main ? [main] : []), ...filled, ...empty];
}

export function ownBalance(a: Account) {
  return a.balance - a.credit_limit;
}

export function accountLabel(a: Account) {
  const name = CURRENCY_NAMES[a.currency_code] ?? CARD_NAMES[a.account_type] ?? 'Рахунок';
  const last4 = a.masked_pan?.slice(-4);
  return last4 ? `${name} · ${last4}` : name;
}
