import { useEffect, useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, useWindowDimensions, View } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withDelay,
  withSpring,
} from 'react-native-reanimated';

import { FONT } from '@/lib/fonts';
import { monthName } from '@/lib/period';
import { useTheme, withAlpha } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Text } from '@/ui/Text';
import type { MonthKey } from '@/ui/TxList';

type Props = {
  // oldest first, like Revolut: the current month sits on the right
  months: MonthKey[];
  active: number;
  onPick: (index: number) => void;
  // months with no transactions are shown faded and can't be picked
  isEnabled?: (m: MonthKey) => boolean;
};

const H = 32;
const INSET = 4;
const SPRING = { duration: 420, dampingRatio: 0.8 };
// the far edge of the pill follows a bit later, so it stretches as it moves
const LAG_MS = 55;

// Glass capsule of months with a pill sliding under the active one
export function MonthStrip({ months, active, onPick, isEnabled }: Props) {
  const { c, dark } = useTheme();
  const { width: screenWidth } = useWindowDimensions();
  const reduceMotion = useReducedMotion();
  const scroll = useRef<ScrollView>(null);
  const layouts = useRef<{ x: number; w: number }[]>([]);
  const [contentWidth, setContentWidth] = useState(0);
  const [placed, setPlaced] = useState(false);
  const left = useSharedValue(0);
  const right = useSharedValue(0);
  const thisYear = new Date().getFullYear();
  // hugs a few months, scrolls when there are many
  const maxWidth = screenWidth - 40 - INSET * 2;
  const width = contentWidth ? Math.min(contentWidth, maxWidth) : maxWidth;

  const centre = (i: number, animated: boolean) => {
    const l = layouts.current[i];
    if (!l) return;
    scroll.current?.scrollTo({ x: Math.max(0, l.x + l.w / 2 - width / 2), animated });
  };

  useEffect(() => {
    const l = layouts.current[active];
    if (!l || !placed) return;
    const toLeft = l.x,
      toRight = l.x + l.w;
    if (reduceMotion) {
      left.set(toLeft);
      right.set(toRight);
    } else if (toLeft < left.get()) {
      left.set(withSpring(toLeft, SPRING));
      right.set(withDelay(LAG_MS, withSpring(toRight, SPRING)));
    } else {
      right.set(withSpring(toRight, SPRING));
      left.set(withDelay(LAG_MS, withSpring(toLeft, SPRING)));
    }
    centre(active, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, placed, reduceMotion]);

  const pill = useAnimatedStyle(() => ({ left: left.value, width: Math.max(0, right.value - left.value) }));
  // the white copy of the labels moves against the pill, so only the part
  // under it shows: the colour flows across with the pill instead of jumping
  const inside = useAnimatedStyle(() => ({ transform: [{ translateX: -left.value }] }));

  const label = (m: MonthKey) => `${monthName(new Date(m.year, m.month, 1))}${m.year !== thisYear ? ` ${m.year}` : ''}`;
  const fill = dark
    ? { backgroundColor: c.accentFill }
    : { experimental_backgroundImage: `linear-gradient(150deg, ${c.cardA}, ${c.cardB})` };

  return (
    <Glass radius={(H + INSET * 2) / 2} blur style={styles.capsule} contentStyle={styles.inner}>
      <ScrollView
        ref={scroll}
        horizontal
        showsHorizontalScrollIndicator={false}
        onContentSizeChange={(w) => setContentWidth(w)}
        style={{ width }}
      >
        {months.map((m, i) => {
          const enabled = isEnabled?.(m) ?? true;
          return (
            <Pressable
              key={`${m.year}-${m.month}`}
              accessibilityRole="tab"
              accessibilityState={{ selected: i === active, disabled: !enabled }}
              disabled={!enabled}
              onPress={() => onPick(i)}
              onLayout={(e) => {
                const { x, width: w } = e.nativeEvent.layout;
                layouts.current[i] = { x, w };
                // first layout, or the months around it changed: snap, no animation
                if (i === active) {
                  left.set(x);
                  right.set(x + w);
                  if (!placed) setPlaced(true);
                  requestAnimationFrame(() => centre(i, false));
                }
              }}
              style={styles.item}
            >
              <Text style={[styles.label, { color: enabled ? c.category.neutral : withAlpha(c.ghost, 0.55) }]}>
                {label(m)}
              </Text>
            </Pressable>
          );
        })}

        <Animated.View pointerEvents="none" style={[styles.pill, fill, { opacity: placed ? 1 : 0 }, pill]}>
          <Animated.View style={[styles.row, { width: contentWidth }, inside]}>
            {months.map((m) => (
              <View key={`${m.year}-${m.month}`} style={styles.item}>
                <Text style={[styles.label, { color: c.onPrimary }]}>{label(m)}</Text>
              </View>
            ))}
          </Animated.View>
        </Animated.View>
      </ScrollView>
    </Glass>
  );
}

const styles = StyleSheet.create({
  capsule: { alignSelf: 'center' },
  inner: { padding: INSET },
  pill: { position: 'absolute', top: 0, height: H, borderRadius: H / 2, overflow: 'hidden' },
  row: { position: 'absolute', top: 0, left: 0, flexDirection: 'row' },
  item: { height: H, paddingHorizontal: 14, justifyContent: 'center' },
  // same weight either way: a width change would re-measure and snap the pill
  label: { fontFamily: FONT.ui.semiBold, fontSize: 13.5 },
});
