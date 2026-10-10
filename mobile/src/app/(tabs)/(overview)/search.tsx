import { router, useFocusEffect } from 'expo-router';
import { Fragment, useCallback, useEffect, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { useAccountCurrencies } from '@/api/accounts';
import { txCurrency, useTransactionPages } from '@/api/transactions';
import { formatMoney, UAH } from '@/lib/money';
import { goBack } from '@/lib/nav';
import { isThisMonth, periodRange, rangeLabel, thisMonth } from '@/lib/period';
import { searchPeriod } from '@/lib/periods';
import { plural } from '@/lib/plural';
import { addRecentSearch, useRecentSearches } from '@/lib/recentSearches';
import { useDebounced } from '@/lib/useDebounced';
import { usePullRefresh } from '@/lib/usePullRefresh';
import { useTheme, withAlpha } from '@/theme';
import { EmptyState } from '@/ui/EmptyState';
import { Glass } from '@/ui/Glass';
import { Icon } from '@/ui/icons/Icon';
import { Pill, PillRow } from '@/ui/Pill';
import { SearchField } from '@/ui/SearchField';
import { Text } from '@/ui/Text';
import { TxList } from '@/ui/TxList';

const MIN_LENGTH = 2;

export default function SearchScreen() {
  const { c } = useTheme();
  const [query, setQuery] = useState('');
  const search = useDebounced(query.trim(), 350);
  const period = searchPeriod.useValue();
  const active = search.length >= MIN_LENGTH;
  const list = useTransactionPages({ search, ...periodRange(period) }, active);
  const pull = usePullRefresh(async () => {
    const result = await list.refetch();
    if (result.isError) throw result.error;
  });
  const currencies = useAccountCurrencies();
  const recent = useRecentSearches();

  const items = active ? (list.data?.pages.flatMap((p) => p.items) ?? []) : [];
  const unique = [...new Map(items.map((t) => [t.id, t])).values()];
  // the server's total counts its wider date range, so it's exact only without dates
  const dated = period.kind !== 'all';
  const found = !active ? 0 : dated || !list.hasNextPage ? unique.length : (list.data?.pages[0]?.total ?? 0);

  // the period is only for this search session
  useEffect(() => () => searchPeriod.set({ kind: 'all' }), []);

  // remember a query once it led somewhere: a result opened or the screen left
  useFocusEffect(
    useCallback(
      () => () => {
        if (found > 0) addRecentSearch(search);
      },
      [found, search],
    ),
  );

  const uah = currencies ? unique.filter((t) => txCurrency(t, currencies) === UAH) : [];
  const spent = uah.filter((t) => t.amount < 0).reduce((s, t) => s + t.amount, 0);
  const income = uah.filter((t) => t.amount > 0).reduce((s, t) => s + t.amount, 0);
  const sums = [
    spent ? formatMoney(spent, UAH, { cents: false }) : '',
    income ? formatMoney(income, UAH, { cents: false, sign: 'always' }) : '',
  ]
    .filter(Boolean)
    .join('  ·  ');

  const header = (
    <View style={styles.header}>
      <View style={styles.bar}>
        <SearchField
          value={query}
          onChangeText={setQuery}
          placeholder="Магазин або отримувач"
          autoFocus
          onSubmitEditing={() => addRecentSearch(query)}
        />
        <Pressable accessibilityRole="button" hitSlop={8} onPress={goBack}>
          <Text variant="bodyStrong" tone="accentText" style={styles.cancel}>
            Скасувати
          </Text>
        </Pressable>
      </View>

      <View style={styles.section}>
        <Text variant="labelCaps" tone="onBackdrop">
          Період
        </Text>
        <PillRow wrap>
          <Pill label="Увесь час" active={period.kind === 'all'} onPress={() => searchPeriod.set({ kind: 'all' })} />
          <Pill label="Цей тиждень" active={period.kind === 'week'} onPress={() => searchPeriod.set({ kind: 'week' })} />
          <Pill label="Цей місяць" active={isThisMonth(period)} onPress={() => searchPeriod.set(thisMonth())} />
          {period.kind === 'custom' ? (
            <Pill
              label={rangeLabel(period.from, period.to)}
              icon="calendar"
              active
              onPress={() => router.push('/period')}
              onClear={() => searchPeriod.set({ kind: 'all' })}
            />
          ) : (
            <Pill label="Свій період" icon="calendar" onPress={() => router.push('/period')} />
          )}
        </PillRow>
      </View>

      {found > 0 ? (
        <View style={styles.summary}>
          <Text variant="labelSection">{plural(found, ['транзакція', 'транзакції', 'транзакцій'])}</Text>
          {/* sums are only exact once every page is in */}
          {!list.hasNextPage && sums ? (
            <Text variant="rowCaption" tone="muted" style={styles.sums}>
              {sums}
            </Text>
          ) : null}
        </View>
      ) : null}
    </View>
  );

  const empty = active ? (
    <Glass>
      <EmptyState icon="search" title="Нічого не знайдено" caption="Спробуй іншу назву або інший період" />
    </Glass>
  ) : recent.length > 0 ? (
    <Glass contentStyle={styles.recent}>
      <Text variant="labelCaps" tone="ghost">
        Нещодавні пошуки
      </Text>
      {recent.map((q, i) => (
        <Fragment key={q}>
          {i > 0 && <View style={[styles.divider, { backgroundColor: withAlpha(c.shade, 0.07) }]} />}
          <Pressable
            accessibilityRole="button"
            onPress={() => setQuery(q)}
            style={({ pressed }) => [styles.recentRow, pressed && styles.pressed]}
          >
            <Icon name="refresh" size={16} color={c.ghost} weight={1.8} />
            <Text style={styles.recentText} numberOfLines={1}>
              {q}
            </Text>
            <Icon name="chevronRight" size={16} color={c.ghost} weight={1.9} />
          </Pressable>
        </Fragment>
      ))}
    </Glass>
  ) : (
    <View />
  );

  return <TxList list={list} header={header} empty={empty} pull={pull} />;
}

const styles = StyleSheet.create({
  // Figma: 20 between the search bar, the period and the recent searches
  header: { gap: 20 },
  bar: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  cancel: { fontSize: 14 },
  section: { gap: 10 },
  summary: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: -6 },
  sums: { fontSize: 12.5, fontVariant: ['tabular-nums'] },
  // Figma: 12 16 4 16
  recent: { paddingTop: 12, paddingHorizontal: 16, paddingBottom: 4 },
  recentRow: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10 },
  recentText: { flex: 1, fontSize: 14, lineHeight: 19 },
  divider: { height: 1 },
  pressed: { opacity: 0.6 },
});
