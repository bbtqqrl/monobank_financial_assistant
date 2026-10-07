import { router } from 'expo-router';
import { useCallback, useEffect, useEffectEvent, useMemo, useRef, useState } from 'react';
import MaskedView from '@react-native-masked-view/masked-view';
import { Platform, StyleSheet, View } from 'react-native';
import Animated, {
  Extrapolation,
  interpolate,
  useAnimatedReaction,
  useAnimatedStyle,
  useDerivedValue,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';
import { scheduleOnRN } from 'react-native-worklets';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAccountCurrencies } from '@/api/accounts';
import { useAllTransactions, useOldestMonth, useTransactionPages, type TxType } from '@/api/transactions';
import { periodDays, periodFlow } from '@/lib/flow';
import { goBack } from '@/lib/nav';
import { monthName, periodRange, rangeLabel, type Period } from '@/lib/period';
import { listJump, listPeriod } from '@/lib/periods';
import { Backdrop } from '@/ui/Backdrop';
import { EmptyState } from '@/ui/EmptyState';
import { FilterPills } from '@/ui/FilterPills';
import { Glass } from '@/ui/Glass';
import { Header } from '@/ui/Header';
import type { IconName } from '@/ui/icons/Icon';
import { MonthCard } from '@/ui/MonthCard';
import { MonthStrip } from '@/ui/MonthStrip';
import { Pill, PillRow } from '@/ui/Pill';
import { TxList, type MonthKey, type TxListHandle } from '@/ui/TxList';

type Filter = 'all' | TxType;

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'Усі' },
  { key: 'expense', label: 'Витрати' },
  { key: 'income', label: 'Дохід' },
  { key: 'transfer', label: 'Перекази' },
];

const EMPTY: Record<Filter, { icon: IconName; title: string; caption: string }> = {
  all: { icon: 'list', title: 'Транзакцій немає', caption: 'Тут зʼявляться твої операції' },
  expense: { icon: 'cart', title: 'Витрат немає', caption: 'Покупок не знайшлося' },
  income: { icon: 'income', title: 'Доходів немає', caption: 'Зарахувань не знайшлося' },
  transfer: { icon: 'repeat', title: 'Переказів немає', caption: 'Переказів не знайшлося' },
};

// how long the pill ignores scrolling after a tap, while the list flies there
const JUMP_LOCK_MS = 900;
// capsule height and the gap above it
const STRIP_SPACE = 48;
// roughly the filters and the first month card
const STRIP_AFTER = 190;

const openSheet = () => router.push({ pathname: '/period', params: { for: 'list' } });

const sameMonth = (a: MonthKey, b: MonthKey) => a.year === b.year && a.month === b.month;

// oldest first, up to this month
function monthsSince(oldest: MonthKey | null | undefined): MonthKey[] {
  const now = new Date();
  const start = oldest ?? { year: now.getFullYear(), month: now.getMonth() };
  const out: MonthKey[] = [];
  for (let d = new Date(start.year, start.month, 1); d <= now; d = new Date(d.getFullYear(), d.getMonth() + 1, 1)) {
    out.push({ year: d.getFullYear(), month: d.getMonth() });
  }
  return out;
}

function MonthSummary({ year, month, onPress }: MonthKey & { onPress: () => void }) {
  const period: Period = { kind: 'month', year, month };
  return (
    <PeriodSummary period={period} title={monthName(new Date(year, month, 1))} aside={String(year)} onPress={onPress} />
  );
}

function PeriodSummary({ period, title, aside, onPress }: {
  period: Period;
  title: string;
  aside?: string;
  onPress: () => void;
}) {
  const all = useAllTransactions(periodRange(period));
  const currencies = useAccountCurrencies();
  const flow = useMemo(
    () => (all.data && currencies ? periodFlow(all.data, currencies) : undefined),
    [all.data, currencies],
  );
  return <MonthCard title={title} aside={aside} flow={flow} days={periodDays(period)} onPress={onPress} />;
}

export default function TransactionsScreen() {
  const insets = useSafeAreaInsets();
  const [filter, setFilter] = useState<Filter>('all');
  const period = listPeriod.useValue();
  const custom = period.kind === 'custom' ? period : null;
  const list = useTransactionPages({ type: filter === 'all' ? undefined : filter, ...periodRange(period) });
  const oldest = useOldestMonth();
  const months = useMemo(() => monthsSince(oldest.data), [oldest.data]);
  const listRef = useRef<TxListHandle>(null);
  const [overlayH, setOverlayH] = useState(0);
  const [active, setActive] = useState<MonthKey>(() => months[months.length - 1]!);
  // a month to scroll to once it's loaded
  const pending = useRef<MonthKey | null>(null);
  const [tries, setTries] = useState(0);
  const lockedUntil = useRef(0);
  const scrollY = useSharedValue(Platform.OS === 'ios' ? -insets.top : 0);
  const [stripShown, setStripShown] = useState(false);

  // each visit starts as the plain feed
  useEffect(
    () => () => {
      listPeriod.set({ kind: 'all' });
      listJump.set(null);
    },
    [],
  );

  const goTo = (m: MonthKey) => {
    setActive(m);
    lockedUntil.current = Date.now() + JUMP_LOCK_MS;
    pending.current = m;
    setTries((n) => n + 1);
  };

  // a month picked in the period sheet
  useEffect(
    () =>
      listJump.subscribe(() => {
        const m = listJump.get();
        if (!m) return;
        listJump.set(null);
        goTo(m);
      }),
    [],
  );

  // scroll once the month is loaded, pulling more pages until it is
  const tryJump = useEffectEvent(() => {
    const m = pending.current;
    if (!m) return;
    if (listRef.current?.scrollToMonth(m)) {
      lockedUntil.current = Date.now() + JUMP_LOCK_MS;
      pending.current = null;
    } else if (list.hasNextPage && !list.isFetchingNextPage) {
      list.fetchNextPage();
    } else if (!list.hasNextPage && !list.isFetching) {
      pending.current = null;
    }
  });
  useEffect(() => {
    tryJump();
  }, [tries, list.data, list.isFetchingNextPage]);

  // the strip shows up once the first month card has gone under the header
  const rest = Platform.OS === 'ios' ? -insets.top : 0;
  const shown = useDerivedValue(() => (scrollY.value > rest + STRIP_AFTER ? 1 : 0));
  const reveal = useDerivedValue(() => withTiming(shown.value, { duration: 220 }));
  useAnimatedReaction(
    () => shown.value,
    (now, before) => {
      if (now !== before) scheduleOnRN(setStripShown, now === 1);
    },
  );
  const stripStyle = useAnimatedStyle(() => ({
    opacity: reveal.value,
    transform: [{ translateY: (1 - reveal.value) * -10 }, { scale: 0.96 + reveal.value * 0.04 }],
  }));
  const fadeStyle = useAnimatedStyle(() => ({
    opacity: interpolate(scrollY.value, [rest, rest + 24], [0, 1], Extrapolation.CLAMP),
  }));

  const monthHeader = useCallback((m: MonthKey) => <MonthSummary year={m.year} month={m.month} onPress={openSheet} />, []);

  const activeIndex = Math.max(
    0,
    months.findIndex((m) => sameMonth(m, active)),
  );

  return (
    <View style={styles.screen}>
      <TxList
        ref={listRef}
        list={list}
        overlayHeight={overlayH}
        floatingHeight={custom ? 0 : STRIP_SPACE}
        scrollY={scrollY}
        monthHeader={custom ? undefined : monthHeader}
        onTopMonth={(m) => {
          if (Date.now() < lockedUntil.current || sameMonth(m, active)) return;
          setActive(m);
        }}
        header={
          <View style={styles.listHeader}>
            {custom ? (
              <>
                <PillRow>
                  <Pill
                    label={rangeLabel(custom.from, custom.to)}
                    icon="calendar"
                    active
                    onPress={openSheet}
                    onClear={() => listPeriod.set({ kind: 'all' })}
                  />
                </PillRow>
                <PeriodSummary period={custom} title={rangeLabel(custom.from, custom.to)} onPress={openSheet} />
              </>
            ) : null}
            <FilterPills options={FILTERS} value={filter} onChange={setFilter} />
          </View>
        }
        empty={
          <Glass>
            <EmptyState {...EMPTY[filter]} />
          </Glass>
        }
      />

      {/* No bar behind the header: the same backdrop is drawn again on top and
          faded out downwards, so the list just melts away under the title. */}
      <Animated.View
        pointerEvents="none"
        style={[styles.fade, { height: overlayH + (custom ? 0 : STRIP_SPACE) + 28 }, fadeStyle]}
      >
        <MaskedView style={StyleSheet.absoluteFill} maskElement={<View style={[StyleSheet.absoluteFill, styles.mask]} />}>
          <Backdrop variant="warm" />
        </MaskedView>
      </Animated.View>
      <View
        pointerEvents="box-none"
        style={[styles.header, { paddingTop: insets.top + 11 }]}
        onLayout={(e) => setOverlayH(e.nativeEvent.layout.height)}
      >
        <Header
          title="Транзакції"
          left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: goBack }}
          right={{ icon: 'search', label: 'Пошук', onPress: () => router.push('/search') }}
        />
      </View>
      {custom ? null : (
        <Animated.View
          pointerEvents={stripShown ? 'box-none' : 'none'}
          style={[styles.strip, { top: overlayH }, stripStyle]}
        >
          <MonthStrip months={months} active={activeIndex} onPick={(i) => goTo(months[i]!)} />
        </Animated.View>
      )}
    </View>
  );
}


const styles = StyleSheet.create({
  screen: { flex: 1 },
  fade: { position: 'absolute', top: 0, left: 0, right: 0 },
  mask: { experimental_backgroundImage: 'linear-gradient(to bottom, #000 0%, #000 55%, transparent 100%)' },
  header: { position: 'absolute', top: 0, left: 0, right: 0, paddingHorizontal: 20, paddingBottom: 8 },
  strip: { position: 'absolute', left: 20, right: 20, alignItems: 'center' },
  listHeader: { gap: 14 },
});
