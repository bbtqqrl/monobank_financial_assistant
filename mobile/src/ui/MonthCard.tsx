import { useEffect } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import Animated, {
  FadeIn,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';

import type { Flow } from '@/lib/flow';
import { FONT } from '@/lib/fonts';
import { formatMoney, UAH } from '@/lib/money';
import { isoDate } from '@/lib/period';
import { useTheme, withAlpha } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Icon, type IconName } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

type Props = {
  title: string;
  // "2026" next to a month name
  aside?: string;
  // opens the period sheet; without it the title is plain
  onPress?: () => void;
  // arrows only make sense for months
  onPrev?: () => void;
  onNext?: () => void;
  // undefined while loading
  flow?: Flow;
  // days to draw bars for, empty to hide the chart
  days: string[];
  // shown instead of the numbers, e.g. for all time
  note?: string;
};

const CHART_H = 34;

// Period summary in the transactions list: what went out and came in, and a
// bar per day of spending
export function MonthCard({ title, aside, onPress, onPrev, onNext, flow, days, note }: Props) {
  const { c } = useTheme();
  const showArrows = !!onPrev || !!onNext;

  return (
    <Glass radius={22} contentStyle={styles.card}>
      <View style={styles.top}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Період: ${title}${aside ? ` ${aside}` : ''}`}
          disabled={!onPress}
          hitSlop={8}
          onPress={onPress}
          style={({ pressed }) => [styles.pick, pressed && styles.pressed]}
        >
          <Animated.View key={title + (aside ?? '')} entering={FadeIn.duration(220)} style={styles.titleRow}>
            <Text style={[styles.title, { color: c.ink }]} numberOfLines={1}>
              {title}
            </Text>
            {aside ? (
              <Text style={[styles.aside, { color: c.ghost }]} numberOfLines={1}>
                {aside}
              </Text>
            ) : null}
          </Animated.View>
          {onPress ? (
            <View style={[styles.chevron, { backgroundColor: withAlpha(c.shade, 0.07) }]}>
              <Icon name="chevronDown" size={13} color={c.inkSoft} weight={2.2} />
            </View>
          ) : null}
        </Pressable>

        {showArrows ? (
          <View style={[styles.arrows, { backgroundColor: withAlpha(c.shade, 0.06) }]}>
            <Arrow icon="chevronLeft" label="Попередній місяць" onPress={onPrev} />
            <View style={[styles.split, { backgroundColor: withAlpha(c.shade, 0.1) }]} />
            <Arrow icon="chevronRight" label="Наступний місяць" onPress={onNext} />
          </View>
        ) : null}
      </View>

      {days.length > 0 ? <Bars days={days} daily={flow?.daily} /> : null}

      {note ? (
        <Text variant="rowCaption" tone="faint" style={styles.note}>
          {note}
        </Text>
      ) : (
        <View style={[styles.stats, { borderTopColor: withAlpha(c.shade, 0.07) }]}>
          {/* the label and arrow already say it's going out, so no minus, as on the balance card */}
          <Stat icon="arrowDown" label="Витрати" tint={c.category.copper} value={flow && -flow.spent} />
          <View style={[styles.statSplit, { backgroundColor: withAlpha(c.shade, 0.07) }]} />
          <Stat icon="arrowUp" label="Надходження" tint={c.category.green} value={flow && flow.income} income />
        </View>
      )}
    </Glass>
  );
}

function Arrow({ icon, label, onPress }: { icon: IconName; label: string; onPress?: () => void }) {
  const { c } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: !onPress }}
      disabled={!onPress}
      hitSlop={6}
      onPress={onPress}
      style={({ pressed }) => [styles.arrow, pressed && styles.pressed]}
    >
      <Icon name={icon} size={16} color={onPress ? c.inkSoft : withAlpha(c.ghost, 0.5)} weight={2} />
    </Pressable>
  );
}

function Stat({ icon, label, tint, value, income = false }: {
  icon: IconName;
  label: string;
  tint: string;
  value: number | undefined;
  income?: boolean;
}) {
  return (
    <View style={styles.stat}>
      <View style={[styles.statIcon, { backgroundColor: withAlpha(tint, 0.14) }]}>
        <Icon name={icon} size={14} color={tint} weight={2.2} />
      </View>
      <View style={styles.statText}>
        <Text variant="rowCaption" tone="faint">
          {label}
        </Text>
        {value === undefined ? (
          <View style={[styles.skeleton, { backgroundColor: withAlpha(tint, 0.12) }]} />
        ) : (
          <Text variant="rowAmount" numberOfLines={1} style={[styles.statValue, income && value > 0 && { color: tint }]}>
            {formatMoney(value, UAH, { cents: false, sign: income && value > 0 ? 'always' : 'auto' })}
          </Text>
        )}
      </View>
    </View>
  );
}

function Bars({ days, daily }: { days: string[]; daily?: Map<string, number> }) {
  const today = isoDate(new Date());
  const max = daily ? Math.max(1, ...days.map((d) => daily.get(d) ?? 0)) : 1;
  return (
    <View style={styles.bars} accessible accessibilityLabel="Витрати по днях">
      {days.map((day) => (
        <Bar
          key={day}
          // square root, so one big purchase doesn't flatten every other day
          ratio={daily ? Math.sqrt(Math.max(0, daily.get(day) ?? 0) / max) : 0}
          future={day > today}
          today={day === today}
        />
      ))}
    </View>
  );
}

function Bar({ ratio, future, today }: { ratio: number; future: boolean; today: boolean }) {
  const { c } = useTheme();
  const reduceMotion = useReducedMotion();
  const h = useSharedValue(0);

  useEffect(() => {
    h.set(withTiming(ratio, { duration: reduceMotion ? 0 : 420 }));
  }, [ratio, reduceMotion, h]);

  const style = useAnimatedStyle(() => ({ height: 3 + h.value * (CHART_H - 3) }));
  const color = future ? withAlpha(c.shade, 0.06) : today ? c.accent : withAlpha(c.accent, ratio > 0 ? 0.42 : 0.14);

  return (
    <View style={styles.barSlot}>
      <Animated.View style={[styles.bar, { backgroundColor: color }, style]} />
    </View>
  );
}

const styles = StyleSheet.create({
  card: { paddingTop: 14, paddingHorizontal: 16, paddingBottom: 12, gap: 14 },
  top: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
  pick: { flexDirection: 'row', alignItems: 'center', gap: 8, flexShrink: 1 },
  titleRow: { flexDirection: 'row', alignItems: 'baseline', gap: 6, flexShrink: 1 },
  title: { fontFamily: FONT.display.medium, fontSize: 22, lineHeight: 27, letterSpacing: -0.22, flexShrink: 1 },
  aside: { fontFamily: FONT.display.medium, fontSize: 15, lineHeight: 19 },
  chevron: { width: 22, height: 22, borderRadius: 11, alignItems: 'center', justifyContent: 'center' },
  arrows: { flexDirection: 'row', alignItems: 'center', borderRadius: 12, height: 32 },
  arrow: { width: 36, height: 32, alignItems: 'center', justifyContent: 'center' },
  split: { width: 1, height: 16 },
  pressed: { opacity: 0.55 },
  bars: { flexDirection: 'row', alignItems: 'flex-end', height: CHART_H, gap: 2 },
  barSlot: { flex: 1, height: CHART_H, justifyContent: 'flex-end' },
  bar: { borderRadius: 2 },
  stats: { flexDirection: 'row', alignItems: 'center', borderTopWidth: 1, paddingTop: 12 },
  stat: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 10 },
  statSplit: { width: 1, alignSelf: 'stretch', marginHorizontal: 12 },
  statIcon: { width: 30, height: 30, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  statText: { flex: 1, gap: 2 },
  statValue: { fontSize: 16, lineHeight: 20 },
  skeleton: { height: 14, width: '70%', borderRadius: 5, marginVertical: 3 },
  note: { fontSize: 12.5 },
});
