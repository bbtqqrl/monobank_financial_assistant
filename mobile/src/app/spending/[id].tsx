import { useLocalSearchParams } from 'expo-router';
import { ActivityIndicator, StyleSheet, View } from 'react-native';

import { useCategoryShares } from '@/api/analytics';
import { useTransactionPages } from '@/api/transactions';
import { categoryLook } from '@/lib/categories';
import { formatMoney } from '@/lib/money';
import { goBack } from '@/lib/nav';
import { periodRange } from '@/lib/period';
import { plural } from '@/lib/plural';
import { useMask } from '@/lib/privacy';
import { usePullRefresh } from '@/lib/usePullRefresh';
import { TEXT } from '@/theme';
import { CategoryChip } from '@/ui/CategoryChip';
import { EmptyState } from '@/ui/EmptyState';
import { Glass } from '@/ui/Glass';
import { Header } from '@/ui/Header';
import { Screen } from '@/ui/Screen';
import { ChangeBadge } from '@/ui/SpendingCard';
import { Text } from '@/ui/Text';
import { TxList } from '@/ui/TxList';

const monthLower = new Intl.DateTimeFormat('uk', { month: 'long' });

// month= 'YYYY-MM', anything else falls back to this month
function monthOf(param: string | undefined) {
  const m = param?.match(/^(\d{4})-(\d{2})$/);
  const now = new Date();
  return m ? { year: Number(m[1]), month: Number(m[2]) - 1 } : { year: now.getFullYear(), month: now.getMonth() };
}

// Analytics › a category of the ring: what it took this month, its share of
// everything, against the month before, and the purchases behind it
export default function CategoryMonthScreen() {
  const params = useLocalSearchParams<{ id: string; month?: string }>();
  const id = Number(params.id);
  const month = monthOf(params.month);
  const mask = useMask();
  const shares = useCategoryShares(month);
  const item = shares.data?.items.find((i) => i.category_id === id);
  const list = useTransactionPages(
    { category: id, ...periodRange({ kind: 'month', year: month.year, month: month.month }) },
    Number.isInteger(id),
  );
  const pull = usePullRefresh(async () => {
    const [s, l] = await Promise.all([shares.refetch(), list.refetch()]);
    if (s.isError) throw s.error;
    if (l.isError) throw l.error;
  });

  const money = (v: number) => mask(formatMoney(v, undefined, { cents: false }));
  const header = (
    <Header
      title={item?.name ?? 'Категорія'}
      small
      status={pull.status}
      left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: goBack }}
    />
  );

  if (!item) {
    return (
      <Screen background="warm">
        {header}
        {shares.isPending ? (
          <ActivityIndicator style={styles.message} />
        ) : (
          <Text tone="faint" style={styles.message}>
            {shares.isError ? 'Не вдалося завантажити категорію' : 'Цього місяця витрат тут немає'}
          </Text>
        )}
      </Screen>
    );
  }

  // only against a month there's history for
  const pct = shares.data?.comparison.complete ? item.change_pct : null;

  return (
    <TxList
      list={list}
      background="warm"
      pull={pull}
      header={
        <View style={styles.top}>
          {header}
          <View style={styles.hero}>
            <CategoryChip {...categoryLook(item.slug, -1)} size={62} radius={22} />
          </View>
          <Glass contentStyle={styles.card}>
            <View style={styles.head}>
              <View style={styles.headText}>
                <Text variant="labelCaps" tone="ghost">
                  Витрачено за {monthLower.format(new Date(month.year, month.month, 1))}
                </Text>
                <Text style={[TEXT.amountXl, styles.amount]}>{money(item.amount)}</Text>
              </View>
              {pct !== null ? <ChangeBadge pct={pct} /> : null}
            </View>
            <Text variant="rowCaption" tone="faint">
              {`${Math.round(item.share)}% усіх витрат · ${plural(item.transaction_count, ['покупка', 'покупки', 'покупок'])}`}
              {pct !== null ? ` · минулого місяця ${money(item.expected)}` : ''}
            </Text>
          </Glass>
        </View>
      }
      empty={
        <Glass>
          <EmptyState icon="cart" title="Покупок немає" caption="Тут будуть покупки цієї категорії за місяць" />
        </Glass>
      }
    />
  );
}

const styles = StyleSheet.create({
  message: { paddingVertical: 40, textAlign: 'center' },
  top: { gap: 12, marginBottom: 8 },
  hero: { alignItems: 'center', paddingBottom: 2 },
  card: { paddingVertical: 14, paddingHorizontal: 16, gap: 6 },
  head: { flexDirection: 'row', alignItems: 'flex-start', gap: 8 },
  headText: { flex: 1, gap: 2 },
  amount: { fontVariant: ['tabular-nums'] },
});
