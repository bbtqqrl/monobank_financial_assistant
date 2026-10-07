import { useMemo, useState } from 'react';
import { ActivityIndicator, Platform, Pressable, RefreshControl, StyleSheet, View } from 'react-native';
import Animated, { useAnimatedScrollHandler, useSharedValue } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAccountCurrencies } from '@/api/accounts';
import { txCurrency, useTransactionPages, type Transaction, type TxType } from '@/api/transactions';
import { formatMoney, UAH } from '@/lib/money';
import { clockLabel, dayKey, dayLabel } from '@/lib/time';
import { txRow } from '@/lib/txRow';
import { goBack } from '@/lib/nav';
import { DayGroup } from '@/ui/DayGroup';
import { EmptyState } from '@/ui/EmptyState';
import { FilterPills } from '@/ui/FilterPills';
import { Glass } from '@/ui/Glass';
import { Header } from '@/ui/Header';
import type { IconName } from '@/ui/icons/Icon';
import { ScrollBackdrop } from '@/ui/ScrollBackdrop';
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
  // offset pages overlap when a new transaction lands between fetches
  const seen = new Set<number>();
  for (const t of items) {
    if (seen.has(t.id)) continue;
    seen.add(t.id);
    const key = dayKey(t.time);
    const last = days[days.length - 1];
    if (last?.key === key) last.items.push(t);
    else days.push({ key, label: dayLabel(t.time), items: [t] });
  }
  return days;
}

export default function TransactionsScreen() {
  const insets = useSafeAreaInsets();
  const [filter, setFilter] = useState<Filter>('all');
  const list = useTransactionPages(filter === 'all' ? undefined : filter);
  const currencies = useAccountCurrencies();
  const top = 11 + (Platform.OS === 'android' ? insets.top : 0);
  const offset = useSharedValue(Platform.OS === 'ios' ? -insets.top : 0);
  const onScroll = useAnimatedScrollHandler((e) => {
    offset.set(e.contentOffset.y);
  });

  const days = useMemo(
    () => (currencies && list.data ? byDay(list.data.pages.flatMap((p) => p.items)) : []),
    [currencies, list.data],
  );

  // a day total only makes sense in one currency, so it sums the hryvnia part
  const total = (items: Transaction[], cur: Map<number, number>) => {
    const sum = items.filter((t) => txCurrency(t, cur) === UAH).reduce((acc, t) => acc + t.amount, 0);
    // also hides days where a transfer out and back cancel out
    return sum === 0 ? undefined : formatMoney(sum, UAH, { cents: false });
  };

  const header = (
    <View style={styles.top}>
      <ScrollBackdrop variant="warm" offset={offset} style={{ top: -top, left: -SIDE }} />
      <Header
        title="Транзакції"
        left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: goBack }}
        right={{ icon: 'search', label: 'Пошук' }}
      />
      <FilterPills options={FILTERS} value={filter} onChange={setFilter} />
    </View>
  );

  const empty = list.isPending || !currencies ? (
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
      <Animated.FlatList
        data={days}
        keyExtractor={(d) => d.key}
        renderItem={({ item }) =>
          currencies ? (
            <DayGroup
              label={item.label}
              total={total(item.items, currencies)}
              rows={item.items.map((t) => txRow(t, currencies, clockLabel(t.time)))}
            />
          ) : null
        }
        ListHeaderComponent={header}
        ListEmptyComponent={empty}
        ListFooterComponent={
          list.isFetchingNextPage ? (
            <ActivityIndicator style={styles.more} />
          ) : list.isFetchNextPageError ? (
            <Pressable accessibilityRole="button" style={styles.more} onPress={() => list.fetchNextPage()}>
              <Text variant="link" tone="accentText" style={styles.retry}>
                Не вдалося довантажити · Спробувати ще
              </Text>
            </Pressable>
          ) : null
        }
        ItemSeparatorComponent={Gap}
        onEndReached={() => {
          if (list.hasNextPage && !list.isFetchingNextPage && !list.isFetchNextPageError) list.fetchNextPage();
        }}
        onEndReachedThreshold={0.6}
        refreshControl={
          <RefreshControl refreshing={list.isRefetching && !list.isFetchingNextPage} onRefresh={() => list.refetch()} />
        }
        onScroll={onScroll}
        scrollEventThrottle={16}
        contentInsetAdjustmentBehavior="automatic"
        contentContainerStyle={[styles.content, { paddingTop: top }]}
      />
    </View>
  );
}

function Gap() {
  return <View style={styles.gap} />;
}

const SIDE = 20;

const styles = StyleSheet.create({
  screen: { flex: 1 },
  // Figma: 14 between blocks on this screen
  top: { gap: 14, marginBottom: 14 },
  content: { paddingHorizontal: SIDE, paddingBottom: 24 },
  gap: { height: 14 },
  loading: { paddingVertical: 40 },
  more: { paddingVertical: 20 },
  retry: { textAlign: 'center' },
  error: { padding: 16, gap: 8 },
});
