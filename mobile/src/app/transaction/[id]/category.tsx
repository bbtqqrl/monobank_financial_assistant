import { router, useLocalSearchParams } from 'expo-router';
import { Alert } from 'react-native';

import { useAccountCurrencies } from '@/api/accounts';
import type { CategoryKind } from '@/api/categories';
import { ApiError } from '@/api/client';
import { txCurrency, useSetCategory, useTransaction } from '@/api/transactions';
import { formatMoney } from '@/lib/money';
import { dayLabel } from '@/lib/time';
import { CategoryPicker } from '@/ui/CategoryPicker';

// money going out is never income, the backend turns that down
const OUTGOING_KINDS: readonly CategoryKind[] = ['expense', 'transfer', 'unknown'];

// Change category sheet over the transaction details (Figma: ChangeCategory)
export default function ChangeCategorySheet() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const tx = useTransaction(Number(id));
  const currencies = useAccountCurrencies();
  const change = useSetCategory(Number(id));
  const t = tx.data;

  const close = () => {
    if (router.canGoBack()) router.back();
    else router.replace({ pathname: '/transaction/[id]', params: { id } });
  };

  const subtitle = t
    ? [t.description, currencies && formatMoney(t.amount, txCurrency(t, currencies)), dayLabel(t.time)]
        .filter(Boolean)
        .join(' · ')
    : '';
  // the backend remembers a purchase's category for its merchant
  const note =
    t && t.mcc !== null && t.amount < 0 ? `Наступні покупки в «${t.description}» теж підуть у цю категорію` : undefined;

  return (
    <CategoryPicker
      title="Змінити категорію"
      subtitle={subtitle}
      note={note}
      selectedId={t?.category?.id ?? null}
      kinds={t && t.amount < 0 ? OUTGOING_KINDS : undefined}
      busyId={change.isPending ? change.variables.id : undefined}
      onPick={(category) => {
        if (!category || category.id === t?.category?.id) {
          close();
          return;
        }
        change.mutate(category, {
          onSuccess: close,
          onError: (error) =>
            Alert.alert(
              'Не вдалося змінити категорію',
              error instanceof ApiError && error.status === 400
                ? 'Ця категорія не підходить для цієї транзакції'
                : 'Перевір інтернет і спробуй ще раз',
            ),
        });
      }}
    />
  );
}
