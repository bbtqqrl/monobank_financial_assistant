import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { z } from 'zod';

import { UAH } from '@/lib/money';

import { api } from './client';

// GET /accounts, same fields as the backend's AccountResponse
const AccountSchema = z.object({
  id: z.number().int(),
  mono_account_id: z.string(),
  account_type: z.string(),
  currency_code: z.number().int(),
  // minor units, includes the credit limit
  balance: z.number().int(),
  credit_limit: z.number().int(),
  masked_pan: z.string().nullable(),
  iban: z.string().nullable(),
  is_active: z.boolean(),
});

export type Account = z.infer<typeof AccountSchema>;

export function useAccounts() {
  return useQuery({ queryKey: ['accounts'], queryFn: () => api(z.array(AccountSchema), '/accounts') });
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

// The user's own order when there is one. Otherwise the main account first,
// then the rest in the bank's order, empty ones at the end; cards opened since
// the user arranged them follow in that same order.
export function sortedAccounts(accounts: Account[], order?: readonly number[] | null): Account[] {
  const main = mainAccount(accounts);
  const rest = accounts.filter((a) => a.is_active && a !== main);
  const filled = rest.filter((a) => ownBalance(a) !== 0);
  const empty = rest.filter((a) => ownBalance(a) === 0);
  const byBank = [...(main ? [main] : []), ...filled, ...empty];
  if (!order) return byBank;
  const rank = new Map(order.map((id, i) => [id, i]));
  const at = (a: Account) => rank.get(a.id) ?? order.length;
  return [...byBank].sort((a, b) => at(a) - at(b));
}

export function ownBalance(a: Account) {
  return a.balance - a.credit_limit;
}

export function accountName(a: Account) {
  return CURRENCY_NAMES[a.currency_code] ?? CARD_NAMES[a.account_type] ?? 'Рахунок';
}

export function accountLabel(a: Account) {
  const last4 = a.masked_pan?.slice(-4);
  return last4 ? `${accountName(a)} · ${last4}` : accountName(a);
}

// undefined until accounts load: amounts can't be labelled before that
export function useAccountCurrencies(): Map<number, number> | undefined {
  const { data } = useAccounts();
  return useMemo(() => data && new Map(data.map((a) => [a.id, a.currency_code])), [data]);
}
