import type { InfiniteData, UseInfiniteQueryResult } from '@tanstack/react-query';
import {
  createContext,
  useContext,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type ReactElement,
  type ReactNode,
  type Ref,
} from 'react';
import {
  ActivityIndicator,
  Dimensions,
  FlatList,
  Platform,
  Pressable,
  RefreshControl,
  StyleSheet,
  View,
  type LayoutChangeEvent,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import Animated, {
  useAnimatedReaction,
  useAnimatedScrollHandler,
  useSharedValue,
  type SharedValue,
} from 'react-native-reanimated';
import { scheduleOnRN } from 'react-native-worklets';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAccountCurrencies } from '@/api/accounts';
import type { TxPage } from '@/api/transactions';
import { byDay, dayTotal, type Day } from '@/lib/days';
import { clockLabel } from '@/lib/time';
import { txRow } from '@/lib/txRow';
import type { BackdropVariant } from '@/ui/Backdrop';
import { DayGroup } from '@/ui/DayGroup';
import { Glass } from '@/ui/Glass';
import { ScrollBackdrop } from '@/ui/ScrollBackdrop';
import { Text } from '@/ui/Text';

export type MonthKey = { year: number; month: number };

export type TxListHandle = {
  // false when that month isn't loaded yet
  scrollToMonth: (m: MonthKey) => boolean;
};

type Item = ({ kind: 'month'; key: string } & MonthKey) | ({ kind: 'day' } & Day);

type Props = {
  list: UseInfiniteQueryResult<InfiniteData<TxPage>>;
  // header, filters and the like, scrolls with the list
  header: ReactNode;
  // shown once loaded with nothing to show
  empty: ReactElement;
  background?: BackdropVariant;
  // a block at the start of every month, e.g. its summary
  monthHeader?: (m: MonthKey) => ReactElement;
  // room for something pinned over the top of the list
  overlayHeight?: number;
  // what floats under that only while scrolled, jumps land below it too
  floatingHeight?: number;
  // content offset, for things that react to scrolling
  scrollY?: SharedValue<number>;
  // the month at the top of the screen while scrolling
  onTopMonth?: (m: MonthKey) => void;
  ref?: Ref<TxListHandle>;
};

const SIDE = 20;
// Animated.FlatList keeps CellRendererComponent for its own layout animations
const ListView = Animated.createAnimatedComponent(FlatList<Item>);

function monthOf(t: number): MonthKey {
  const d = new Date(t * 1000);
  return { year: d.getFullYear(), month: d.getMonth() };
}

const monthKey = (m: MonthKey) => `m-${m.year}-${m.month}`;

// Transactions grouped by day on glass cards, loaded page by page
export function TxList({
  list,
  header,
  empty,
  background = 'warm',
  monthHeader,
  overlayHeight = 0,
  floatingHeight = 0,
  scrollY,
  onTopMonth,
  ref,
}: Props) {
  const insets = useSafeAreaInsets();
  const currencies = useAccountCurrencies();
  const listRef = useRef<FlatList<Item>>(null);
  // iOS already insets the content by the status bar
  const covered = overlayHeight > 0 ? overlayHeight - (Platform.OS === 'ios' ? insets.top : 0) : 0;
  const top = 11 + covered + (Platform.OS === 'android' && !overlayHeight ? insets.top : 0);
  const offset = useSharedValue(Platform.OS === 'ios' ? -insets.top : 0);
  const onScroll = useAnimatedScrollHandler((e) => {
    offset.set(e.contentOffset.y);
    scrollY?.set(e.contentOffset.y);
  });
  const landAt = overlayHeight + floatingHeight + 11;

  const items = useMemo<Item[]>(() => {
    if (!currencies || !list.data) return [];
    const days = byDay(list.data.pages.flatMap((p) => p.items));
    if (!monthHeader) return days.map((d) => ({ kind: 'day' as const, ...d }));
    const out: Item[] = [];
    let last = '';
    for (const d of days) {
      const m = monthOf(d.items[0]!.time);
      const key = monthKey(m);
      if (key !== last) out.push({ kind: 'month', key, ...m });
      last = key;
      out.push({ kind: 'day', ...d });
    }
    return out;
  }, [currencies, list.data, monthHeader]);

  // Where each month card sits in the content, so the month under the header
  // is known exactly. Viewability can't help: it counts what the header hides.
  const starts = useRef(new Map<string, { y: number } & MonthKey>());
  const monthYs = useSharedValue<({ y: number } & MonthKey)[]>([]);
  // a card that wasn't rendered yet when asked to scroll to it
  const aimAt = useRef<string | null>(null);
  const landRef = useRef(landAt);
  useEffect(() => {
    landRef.current = landAt;
  }, [landAt]);

  // content offset is content y minus where it should show on screen
  // a content y shows on screen at y minus the offset, in both platforms
  const [scrollToY] = useState(
    () => (y: number) => listRef.current?.scrollToOffset({ offset: y - landRef.current, animated: true }),
  );

  // A card far below isn't rendered, so its place is unknown and FlatList can't
  // scroll to it either. Walk down a few screens at a time until it renders;
  // its layout then aims at it exactly.
  const [stepToward] = useState(() => {
    const step = (key: string, last: number, tries: number) => {
      if (aimAt.current !== key || tries > 60) return;
      const now = offset.get();
      // didn't move: the end of the list, give up
      if (tries > 0 && Math.abs(now - last) < 1) {
        aimAt.current = null;
        return;
      }
      listRef.current?.scrollToOffset({ offset: now + Dimensions.get('window').height * 2, animated: false });
      setTimeout(() => step(key, now, tries + 1), 32);
    };
    return (key: string) => step(key, Number.NaN, 0);
  });

  const [onCellLayout] = useState(() => (item: Item, y: number) => {
    if (item.kind !== 'month') return;
    starts.current.set(item.key, { y, year: item.year, month: item.month });
    monthYs.set([...starts.current.values()].sort((a, b) => a.y - b.y));
    if (aimAt.current === item.key) {
      aimAt.current = null;
      scrollToY(y);
    }
  });

  useImperativeHandle(
    ref,
    () => ({
      scrollToMonth: (m) => {
        // a month without transactions lands on the next older one
        const target = m.year * 12 + m.month;
        const index = items.findIndex((i) => i.kind === 'month' && i.year * 12 + i.month <= target);
        const item = items[index];
        if (!item || item.kind !== 'month') return false;
        const known = starts.current.get(item.key);
        if (known) {
          scrollToY(known.y);
        } else {
          // not rendered yet: get it on screen, then aim exactly once it's measured
          aimAt.current = item.key;
          stepToward(item.key);
        }
        return true;
      },
    }),
    [items, scrollToY, stepToward],
  );

  const onTopMonthRef = useRef(onTopMonth);
  useEffect(() => {
    onTopMonthRef.current = onTopMonth;
  }, [onTopMonth]);
  const reportTop = (year: number, month: number) => onTopMonthRef.current?.({ year, month });
  useAnimatedReaction(
    () => {
      const line = offset.value + overlayHeight + floatingHeight + 24;
      const ys = monthYs.value;
      let found = -1;
      for (let i = 0; i < ys.length; i++) if (ys[i]!.y <= line) found = i;
      return found < 0 ? (ys.length ? 0 : -1) : found;
    },
    (i, before) => {
      if (i === before || i < 0) return;
      const m = monthYs.value[i]!;
      scheduleOnRN(reportTop, m.year, m.month);
    },
  );

  // a disabled query (nothing to search yet) is pending but idle
  const waiting = (list.isPending && list.fetchStatus !== 'idle') || !currencies;
  const placeholder = waiting ? (
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
    empty
  );

  return (
    <View style={styles.screen}>
      <CellLayout.Provider value={onCellLayout}>
        <ListView
          ref={listRef}
          data={items}
          keyExtractor={(i) => i.key}
          renderItem={({ item }) =>
            item.kind === 'month' ? (
              (monthHeader?.(item) ?? null)
            ) : currencies ? (
              <DayGroup
                label={item.label}
                total={dayTotal(item.items, currencies)}
                rows={item.items.map((t) => txRow(t, currencies, clockLabel(t.time)))}
              />
            ) : null
          }
          ListHeaderComponent={
            <View style={styles.top}>
              <ScrollBackdrop variant={background} offset={offset} style={{ top: -top, left: -SIDE }} />
              {header}
            </View>
          }
          ListEmptyComponent={placeholder}
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
          CellRendererComponent={monthHeader ? Cell : undefined}
          refreshControl={
            <RefreshControl
              refreshing={list.isRefetching && !list.isFetchingNextPage}
              onRefresh={() => list.refetch()}
              progressViewOffset={covered}
            />
          }
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="on-drag"
          onScroll={onScroll}
          scrollEventThrottle={16}
          contentInsetAdjustmentBehavior="automatic"
          scrollIndicatorInsets={{ top: covered }}
          contentContainerStyle={[styles.content, { paddingTop: top }]}
        />
      </CellLayout.Provider>
    </View>
  );
}

const CellLayout = createContext<(item: Item, y: number) => void>(() => {});

type CellProps = {
  item: Item;
  children: ReactNode;
  style: StyleProp<ViewStyle> | undefined;
  onLayout?: (e: LayoutChangeEvent) => void;
};

// a list cell that also reports where it landed
function Cell({ item, children, style, onLayout }: CellProps) {
  const report = useContext(CellLayout);
  return (
    <View
      style={style}
      onLayout={(e) => {
        onLayout?.(e);
        report(item, e.nativeEvent.layout.y);
      }}
    >
      {children}
    </View>
  );
}

function Gap() {
  return <View style={styles.gap} />;
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  // Figma: 14 between blocks on these screens
  top: { gap: 14, marginBottom: 14 },
  content: { paddingHorizontal: SIDE, paddingBottom: 24 },
  gap: { height: 14 },
  loading: { paddingVertical: 40 },
  more: { paddingVertical: 20 },
  retry: { textAlign: 'center' },
  error: { padding: 16, gap: 8 },
});
