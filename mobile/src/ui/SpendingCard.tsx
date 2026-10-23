import { useState } from 'react';
import { ActivityIndicator, StyleSheet, View, type LayoutChangeEvent } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { useSharedValue } from 'react-native-reanimated';
import Svg, { Circle, Defs, Line, LinearGradient, Path, Stop } from 'react-native-svg';
import { scheduleOnRN } from 'react-native-worklets';

import type { Spending } from '@/api/analytics';
import { balanceHidden } from '@/lib/cardOrder';
import { compactUah, niceTop, smoothPath } from '@/lib/chart';
import { FONT } from '@/lib/fonts';
import { tap } from '@/lib/haptics';
import { formatMoney } from '@/lib/money';
import { parseIso, rangeLabel } from '@/lib/period';
import { MASK } from '@/lib/privacy';
import { TEXT, useTheme, withAlpha } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Text } from '@/ui/Text';

const CHART_H = 112;
const AXIS_W = 44;
// room for the end dot so it isn't cut at the top and right
const PAD = 5;
// a sideways drag reads the chart, an up-and-down one still scrolls the screen
const DRAG_X = 8;
const DRAG_Y = 12;

const monthLower = new Intl.DateTimeFormat('uk', { month: 'long' });
const monthShort = new Intl.DateTimeFormat('uk', { month: 'short' });
const dayMonth = new Intl.DateTimeFormat('uk', { day: 'numeric', month: 'long' });

type Props = {
  // month is 0-based, like Date
  year: number;
  month: number;
  spending?: Spending;
};

// Less than the same days last month is good news, so it's green
export function ChangeBadge({ pct }: { pct: number }) {
  const { c } = useTheme();
  const rounded = Math.round(Math.abs(pct));
  const less = pct < 0;
  // text colours: the deeper green and red that read on glass
  const tone = rounded === 0 ? c.faint : less ? c.positive : c.dangerText;
  const label = rounded === 0 ? 'як минулого місяця' : `${less ? '↓' : '↑'} ${rounded}% ${less ? 'менше' : 'більше'}`;
  return (
    <View
      style={[styles.badge, { backgroundColor: withAlpha(tone, 0.12) }]}
      accessibilityLabel={rounded === 0 ? 'Як минулого місяця' : `На ${rounded}% ${less ? 'менше' : 'більше'}, ніж минулого місяця`}
    >
      <Text variant="link" style={{ color: tone }}>
        {label}
      </Text>
    </View>
  );
}

// What a month cost so far, against the same days of the month before, and
// how it added up day by day. A finger along the chart reads any day.
// (Figma: Аналітика › Підсумок)
export function SpendingCard({ year, month, spending }: Props) {
  const { c, dark } = useTheme();
  const hidden = balanceHidden.useValue();
  const [width, setWidth] = useState(0);
  const onLayout = (e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width);
  // the day under the finger, an index into daily
  const [active, setActive] = useState<number | null>(null);
  const activeOnUi = useSharedValue(-1);

  const money = (v: number) => (hidden ? MASK : formatMoney(v, undefined, { cents: false }));
  const daily = spending?.daily ?? [];
  const days = new Date(year, month + 1, 0).getDate();
  const top = niceTop(spending?.total ?? 0);
  const plotW = Math.max(0, width - AXIS_W - PAD);
  const x = (i: number) => AXIS_W + (days > 1 ? (i / (days - 1)) * plotW : 0);
  const y = (v: number) => PAD + (1 - v / top) * (CHART_H - PAD * 2);
  const points = daily.map((d, i) => ({ x: x(i), y: y(d.amount) }));
  const line = smoothPath(points);
  const last = points[points.length - 1];
  const area = last ? `${line} L${last.x},${y(0)} L${x(0)},${y(0)} Z` : '';
  const ticks = [top, top / 2, 0];
  const dayLabels = [1, 8, 15, 22, days];
  const short = monthShort.format(new Date(year, month, 1)).replace('.', '');

  const pick = (i: number | null) => {
    if (i !== null) tap();
    setActive(i);
  };
  const count = daily.length;
  const read = Gesture.Pan()
    .activeOffsetX([-DRAG_X, DRAG_X])
    .failOffsetY([-DRAG_Y, DRAG_Y])
    .onBegin(() => {
      activeOnUi.set(-1);
    })
    .onUpdate((e) => {
      if (count === 0 || plotW <= 0) return;
      const raw = Math.round(((e.x - AXIS_W) / plotW) * (days - 1));
      const i = Math.min(count - 1, Math.max(0, raw));
      if (i === activeOnUi.get()) return;
      activeOnUi.set(i);
      scheduleOnRN(pick, i);
    })
    .onFinalize(() => {
      activeOnUi.set(-1);
      scheduleOnRN(pick, null);
    });

  // under the total: the day being read, or what the month is compared with
  const point = active !== null ? daily[active] : undefined;
  const cmp = spending?.comparison;
  const note = point
    ? `${dayMonth.format(parseIso(point.date))}: ${money(point.amount)}${
        active ? ` · за день ${money(point.amount - (daily[active - 1]?.amount ?? 0))}` : ''
      }`
    : !cmp
      ? ' '
      : cmp.complete
        ? `${rangeLabel(cmp.start, cmp.end)}: ${money(cmp.total)}`
        : 'Для порівняння ще замало історії';
  const marker = active !== null ? points[active] : undefined;

  return (
    <Glass contentStyle={styles.card}>
      <View style={styles.head}>
        <View style={styles.headText}>
          <Text variant="labelCaps" tone="ghost">
            Витрачено за {monthLower.format(new Date(year, month, 1))}
          </Text>
          <Text style={[TEXT.amountXl, styles.amount]}>{spending ? money(spending.total) : ' '}</Text>
          <Text variant="rowCaption" tone={point ? 'ink' : 'faint'} numberOfLines={1} style={styles.note}>
            {note}
          </Text>
        </View>
        {/* without history behind it, the comparison would mislead */}
        {spending?.change_pct != null && spending.comparison.complete ? <ChangeBadge pct={spending.change_pct} /> : null}
      </View>

      <GestureDetector gesture={read}>
        <View
          style={styles.chart}
          onLayout={onLayout}
          accessible
          accessibilityLabel="Витрати по днях"
          accessibilityHint="Проведи пальцем уздовж графіка, щоб побачити будь-який день"
        >
          {!spending ? (
            <ActivityIndicator style={styles.loading} />
          ) : width > 0 ? (
            <Svg width={width} height={CHART_H}>
              <Defs>
                <LinearGradient id="spent" x1="0" y1="0" x2="0" y2="1">
                  <Stop offset="0" stopColor={c.accent} stopOpacity={dark ? 0.3 : 0.22} />
                  <Stop offset="1" stopColor={c.accent} stopOpacity={0} />
                </LinearGradient>
              </Defs>
              {ticks.map((t) => (
                <Line
                  key={t}
                  x1={AXIS_W}
                  x2={width - PAD}
                  y1={y(t)}
                  y2={y(t)}
                  stroke={withAlpha(c.shade, dark ? 0.14 : 0.08)}
                  strokeWidth={1}
                />
              ))}
              {area ? <Path d={area} fill="url(#spent)" /> : null}
              {line ? <Path d={line} fill="none" stroke={c.accent} strokeWidth={2.2} strokeLinecap="round" /> : null}
              {marker ? (
                <Line
                  x1={marker.x}
                  x2={marker.x}
                  y1={PAD}
                  y2={y(0)}
                  stroke={withAlpha(c.ink, 0.25)}
                  strokeWidth={1}
                  strokeDasharray="3 3"
                />
              ) : null}
              {(marker ?? last) ? (
                <Circle
                  cx={(marker ?? last)!.x}
                  cy={(marker ?? last)!.y}
                  r={marker ? 5 : 4}
                  fill={c.accent}
                  stroke={c.bg}
                  strokeWidth={2}
                />
              ) : null}
            </Svg>
          ) : null}
          {spending && width > 0
            ? ticks.map((t) => (
                <Text key={t} numberOfLines={1} style={[styles.axis, styles.tick, { top: y(t) - 7, color: c.ghost }]}>
                  {hidden && t > 0 ? MASK : compactUah(t / 100)}
                </Text>
              ))
            : null}
        </View>
      </GestureDetector>

      {width > 0 ? (
        <View style={styles.days}>
          {dayLabels.map((d, i) => (
            <Text
              key={d}
              style={[
                styles.axis,
                styles.day,
                { left: x(d - 1) - 20, color: c.ghost },
                i === dayLabels.length - 1 && styles.dayLast,
              ]}
            >
              {i === 0 ? `1 ${short}` : d}
            </Text>
          ))}
        </View>
      ) : null}
    </Glass>
  );
}

const styles = StyleSheet.create({
  card: { paddingTop: 14, paddingHorizontal: 16, paddingBottom: 12, gap: 10 },
  head: { flexDirection: 'row', alignItems: 'flex-start', gap: 8 },
  headText: { flex: 1, gap: 2 },
  amount: { fontVariant: ['tabular-nums'] },
  note: { fontVariant: ['tabular-nums'] },
  badge: { paddingHorizontal: 10, paddingVertical: 5, borderRadius: 11 },
  chart: { height: CHART_H },
  loading: { marginTop: CHART_H / 2 - 10 },
  axis: { position: 'absolute', fontFamily: FONT.ui.medium, fontSize: 10, fontVariant: ['tabular-nums'] },
  tick: { left: 0, width: AXIS_W - 6 },
  days: { height: 14 },
  day: { width: 40, textAlign: 'center' },
  dayLast: { textAlign: 'right', left: undefined, right: 0 },
});
