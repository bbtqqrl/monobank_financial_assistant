import { router } from 'expo-router';

import { foreignPart, txCurrency, type Transaction } from '@/api/transactions';
import { categoryLook } from '@/lib/categories';

// Props for <TxRow> from an API transaction. `when` differs by screen:
// "Вчора" in short lists, just the time under a day header.
export function txRow(t: Transaction, accountCurrency: Map<number, number>, when: string) {
  return {
    key: t.id,
    look: categoryLook(t.category?.slug, t.amount),
    title: t.description,
    caption: t.category?.name ?? 'Без категорії',
    amount: t.amount,
    currency: txCurrency(t, accountCurrency),
    original: foreignPart(t, accountCurrency),
    when,
    onPress: () => router.push({ pathname: '/transaction/[id]', params: { id: String(t.id) } }),
  };
}
