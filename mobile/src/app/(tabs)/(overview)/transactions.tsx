import { router } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, FlatList, Platform, Pressable, RefreshControl, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAccountCurrencies } from '@/api/accounts';
import { txCurrency, useTransactionPages, type Transaction, type TxType } from '@/api/transactions';
import { formatMoney, UAH } from '@/lib/money';
import { clockLabel, dayKey, dayLabel } from '@/lib/time';
import { txRow } from '@/lib/txRow';
import { Backdrop } from '@/ui/Backdrop';
import { DayGroup } from '@/ui/DayGroup';
import { EmptyState } from '@/ui/EmptyState';
import { FilterPills } from '@/ui/FilterPills';
import { Glass } from '@/ui/Glass';
import { Header } from '@/ui/Header';
import type { IconName } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

type Filter = 'all' | TxType;

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'Усі' },
  { key: 'expense', label: 'Витрати' },
  { key: 'income', label: 'Дохід' },
  { key: 'transfer', label: 'Перекази' },
];

const EMPTY: Record<Filter, { icon: IconName; title: string; caption: string }> = {
  all: { icon: 'list', title: 'Транзакцій ще немає', caption: 'Щойно monobank надішле операції, вони зʼявляться тут' },
  expense: { icon: 'cart', title: 'Витрат немає', caption: 'Тут зʼявляться твої покупки' },
  income: { icon: 'income', title: 'Доходів немає', caption: 'Зарахування й поповнення зʼявляться тут' },
  transfer: { icon: 'repeat', title: 'Переказів немає', caption: 'Переказів між власними рахунками ще не було' },
};

type Day = { key: string; label: string; items: Transaction[] };

// pages come newest first, so a day's transactions are always next to each other
function byDay(items: Transaction[]): Day[] {
  const days: Day[] = [];
  for (const t of items) {
    const key = dayKey(t.time);
    const last = days[days.length - 1];
    if (last?.key === key) last.items.push(t);
    else days.push({ key, label: dayLabel(t.time), items: [t] });
  }
  return days;
}

export default function TransactionsScreen() {
  const insets = useSafeAreaInsets();
  // the design opens this list on spendings
  const [filter, setFilter] = useState<Filter>('expense');
  const list = useTransactionPages(filter === 'all' ? undefined : filter);
  const currencies = useAccountCurrencies();

  const days = byDay(list.data?.pages.flatMap((p) => p.items) ?? []);

  // a day total only makes sense in one currency, so it sums the hryvnia part
  const total = (items: Transaction[]) => {
    const sum = items.filter((t) => txCurrency(t, currencies) === UAH).reduce((acc, t) => acc + t.amount, 0);
    // also hides days where a transfer out and back cancel out
    return sum === 0 ? undefined : formatMoney(sum, UAH, { cents: false });
  };

  const header = (
    <View style={styles.top}>
      <Header
        title="Транзакції"
        left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: () => router.back() }}
        right={{ icon: 'search', label: 'Пошук' }}
      />
      <FilterPills options={FILTERS} value={filter} onChange={setFilter} />
    </View>
  );

  const empty = list.isPending ? (
    <ActivityIndicator style={styles.loading} />
  ) : list.isError ? (
    <Glass contentStyle={styles.error}>
      <Text tone="danger">Не вдалося завантажити транзакції</Text>
      <Pressable accessibilityRole="button" hitSlop={8} onPress={() => list.refetch()}>
        <Text variant="link" tone="accentText">
          Спробувати ще
        </Text>
      </Pressable>
    </Glass>
  ) : (
    <Glass>
      <EmptyState {...EMPTY[filter]} />
    </Glass>
  );

  return (
    <View style={styles.screen}>
      <Backdrop variant="warm" />
      <FlatList
        data={days}
        keyExtractor={(d) => d.key}
        renderItem={({ item }) => (
          <DayGroup
            label={item.label}
            total={total(item.items)}
            rows={item.items.map((t) => txRow(t, currencies, clockLabel(t.time)))}
          />
        )}
        ListHeaderComponent={header}
        ListEmptyComponent={empty}
        ListFooterComponent={list.isFetchingNextPage ? <ActivityIndicator style={styles.more} /> : null}
        ItemSeparatorComponent={Gap}
        onEndReached={() => {
          if (list.hasNextPage && !list.isFetchingNextPage) list.fetchNextPage();
        }}
        onEndReachedThreshold={0.6}
        refreshControl={<RefreshControl refreshing={list.isRefetching} onRefresh={() => list.refetch()} />}
        contentInsetAdjustmentBehavior="automatic"
        contentContainerStyle={[styles.content, { paddingTop: 11 + (Platform.OS === 'android' ? insets.top : 0) }]}
      />
    </View>
  );
}

function Gap() {
  return <View style={styles.gap} />;
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  // Figma: 14 between blocks on this screen
  top: { gap: 14, marginBottom: 14 },
  content: { paddingHorizontal: 20, paddingBottom: 24 },
  gap: { height: 14 },
  loading: { paddingVertical: 40 },
  more: { paddingVertical: 20 },
  error: { padding: 16, gap: 8 },
});
