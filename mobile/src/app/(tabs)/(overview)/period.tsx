import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { rangeDays, rangeLabel } from '@/lib/period';
import { useFeedMonths } from '@/api/transactions';
import { listJump, periodStore } from '@/lib/periods';
import { plural } from '@/lib/plural';
import { useTheme, withAlpha } from '@/theme';
import { Button } from '@/ui/Button';
import { FilterPills } from '@/ui/FilterPills';
import { Icon } from '@/ui/icons/Icon';
import { MonthGrid } from '@/ui/MonthGrid';
import { RangeCalendar } from '@/ui/RangeCalendar';
import { Text } from '@/ui/Text';

type Tab = 'month' | 'custom';

const TABS: { key: Tab; label: string }[] = [
  { key: 'month', label: 'Місяць' },
  { key: 'custom', label: 'Свій період' },
];

// Period sheet. For the transactions list a month is a place to scroll to and
// a custom range a filter; search only gets the range (it has its own presets).
export default function PeriodSheet() {
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ for?: string }>();
  const forList = params.for === 'list';
  const store = periodStore(forList ? 'list' : 'search');
  const current = store.useValue();
  const { months, isEnabled } = useFeedMonths();

  const [tab, setTab] = useState<Tab>(forList && current.kind !== 'custom' ? 'month' : 'custom');
  const [from, setFrom] = useState(current.kind === 'custom' ? current.from : undefined);
  const [to, setTo] = useState(current.kind === 'custom' ? current.to : undefined);
  const end = to ?? from;

  const subtitle =
    tab === 'month'
      ? 'Перейти до місяця'
      : from && end
        ? `${rangeLabel(from, end)} · ${plural(rangeDays(from, end), ['день', 'дні', 'днів'])}`
        : 'Обери перший і останній день';

  const close = () => (router.canGoBack() ? router.back() : router.replace('/transactions'));

  return (
    <View style={[styles.sheet, { paddingBottom: Math.max(insets.bottom, 16) }]}>
      <View style={styles.head}>
        <View style={styles.titles}>
          <Text variant="screenTitle">{forList ? 'Період' : 'Свій період'}</Text>
          <Text variant="rowCaption" tone="faint" style={styles.subtitle}>
            {subtitle}
          </Text>
        </View>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Закрити"
          hitSlop={8}
          onPress={close}
          style={[styles.close, { backgroundColor: withAlpha(c.shade, 0.06) }]}
        >
          <Icon name="close" size={18} color={c.inkSoft} weight={1.9} />
        </Pressable>
      </View>

      {forList ? <FilterPills options={TABS} value={tab} onChange={setTab} /> : null}

      {tab === 'month' ? (
        <>
          <MonthGrid
            isEnabled={isEnabled}
            minYear={months[0]?.year}
            onPick={(year, month) => {
              store.set({ kind: 'all' });
              listJump.set({ year, month });
              close();
            }}
          />
          {current.kind !== 'all' ? (
            <Button
              kind="secondary"
              label="Увесь час"
              onPress={() => {
                store.set({ kind: 'all' });
                close();
              }}
            />
          ) : null}
        </>
      ) : (
        <>
          <RangeCalendar
            from={from}
            to={to}
            onChange={(f, t) => {
              setFrom(f);
              setTo(t);
            }}
          />
          <View style={styles.buttons}>
            <View style={styles.reset}>
              <Button
                kind="secondary"
                label="Скинути"
                disabled={!from}
                onPress={() => {
                  setFrom(undefined);
                  setTo(undefined);
                }}
              />
            </View>
            <View style={styles.apply}>
              <Button
                label="Застосувати"
                disabled={!from}
                onPress={() => {
                  if (!from || !end) return;
                  store.set({ kind: 'custom', from, to: end });
                  close();
                }}
              />
            </View>
          </View>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  sheet: { paddingTop: 22, paddingHorizontal: 20, gap: 16 },
  head: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  titles: { gap: 3, flexShrink: 1 },
  subtitle: { fontSize: 12.5 },
  close: { width: 38, height: 38, borderRadius: 13, alignItems: 'center', justifyContent: 'center' },
  buttons: { flexDirection: 'row', gap: 10, marginTop: 4 },
  reset: { width: 120 },
  apply: { flex: 1 },
});
