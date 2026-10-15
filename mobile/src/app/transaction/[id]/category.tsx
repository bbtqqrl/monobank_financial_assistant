import { router, useLocalSearchParams } from 'expo-router';
import { Alert } from 'react-native';

import { useAccountCurrencies } from '@/api/accounts';
import type { CategoryKind } from '@/api/categories';
import { ApiError } from '@/api/client';
import { isUncategorized, isUnsure, txCurrency, useSetCategory, useTransaction, type Transaction } from '@/api/transactions';
import { formatMoney } from '@/lib/money';
import { dayLabel } from '@/lib/time';
import { useMask } from '@/lib/privacy';
import { CategoryPicker } from '@/ui/CategoryPicker';

// Categories that fit the money's direction. Going out it's never income (the
// backend turns that down). Coming in it's income, unless it may be a refund:
// already in a spending category, or with no category to tell.
function kindsFor(t: Transaction): readonly CategoryKind[] {
  if (t.amount < 0) return ['expense', 'transfer'];
  if (t.category?.kind === 'expense' || isUncategorized(t)) return ['expense', 'income', 'transfer'];
  return ['income', 'transfer'];
}

// Change category sheet over the transaction details (Figma: ChangeCategory)
export default function ChangeCategorySheet() {
  // scope=merchant: the merchant's other purchases move too
  const { id, scope } = useLocalSearchParams<{ id: string; scope?: string }>();
  const mask = useMask();
  const tx = useTransaction(Number(id));
  const currencies = useAccountCurrencies();
  const change = useSetCategory(Number(id));
  const t = tx.data;

  const close = () => {
    if (router.canGoBack()) router.back();
    else router.replace({ pathname: '/transaction/[id]', params: { id } });
  };

  const subtitle = t
    ? [t.description, currencies && mask(formatMoney(t.amount, txCurrency(t, currencies))), dayLabel(t.time)]
        .filter(Boolean)
        .join(' · ')
    : '';
  // a merchant the backend remembers can be moved as a whole
  const mappingId = t?.source !== 'manual' ? (t?.merchant_mapping_id ?? undefined) : undefined;
  const merchant = scope === 'merchant' && mappingId !== undefined;
  // changed by hand ones keep theirs, that's the backend's rule
  const note = t && merchant ? `Для всіх транзакцій «${t.description}»` : undefined;

  return (
    <CategoryPicker
      title={merchant ? 'Усі покупки мерчанта' : 'Змінити категорію'}
      subtitle={subtitle}
      note={note}
      selectedId={t?.category?.id ?? null}
      kinds={t ? kindsFor(t) : undefined}
      busyId={change.isPending ? change.variables.category.id : undefined}
      onPick={(category) => {
        if (!t || !category) {
          close();
          return;
        }
        // the same category again still counts when it confirms an unsure
        // guess or goes to the whole merchant
        if (category.id === t.category?.id && !merchant && !isUnsure(t)) {
          close();
          return;
        }
        change.mutate(
          { category, mappingId: merchant ? mappingId : undefined },
          {
            onSuccess: close,
            onError: (error) =>
              Alert.alert(
                'Не вдалося змінити категорію',
                error instanceof ApiError && error.status === 400
                  ? 'Ця категорія не підходить для цієї транзакції'
                  : 'Перевір інтернет і спробуй ще раз',
              ),
          },
        );
      }}
    />
  );
}
