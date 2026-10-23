import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';

import type { CategoryShares } from '@/api/analytics';
import { categoryLook } from '@/lib/categories';
import { FONT } from '@/lib/fonts';
import { formatMoney } from '@/lib/money';
import { useMask } from '@/lib/privacy';
import { useTheme, withAlpha, type Colors } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Text } from '@/ui/Text';

const SIZE = 112;
const STROKE = 15;
// a sliver of space between the slices, in degrees
const GAP = 3;

type Slice = { key: string; name: string; share: number; color: string; categoryId?: number };

// Each category in its own colour; two that share one get the next free
// colour, so the ring never shows one slice twice
function slicesOf(data: CategoryShares, c: Colors): Slice[] {
  const palette = Object.values(c.category);
  const used = new Set<string>();
  const slices: Slice[] = data.items.map((item) => {
    let color = c.category[categoryLook(item.slug, -1).color];
    if (used.has(color)) color = palette.find((p) => !used.has(p) && p !== c.category.dim) ?? color;
    used.add(color);
    return { key: String(item.category_id), name: item.name, share: item.share, color, categoryId: item.category_id };
  });
  if (data.other && data.other.amount > 0) {
    // paler than any category, the «Інші витрати» one included
    slices.push({ key: 'other', name: 'Інше', share: data.other.share, color: withAlpha(c.category.dim, 0.45) });
  }
  return slices;
}

function arc(from: number, to: number) {
  const r = (SIZE - STROKE) / 2;
  const at = (deg: number) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return `${SIZE / 2 + r * Math.cos(rad)},${SIZE / 2 + r * Math.sin(rad)}`;
  };
  return `M${at(from)} A${r},${r} 0 ${to - from > 180 ? 1 : 0} 1 ${at(to)}`;
}

// Each slice's path around the ring, null for one that is the whole ring
function arcsOf(slices: Slice[]) {
  const total = slices.reduce((sum, x) => sum + x.share, 0);
  const gap = slices.length > 1 ? GAP / 2 : 0;
  const starts = slices.map((_, i) => slices.slice(0, i).reduce((sum, x) => sum + x.share, 0));
  return slices.map((s, i) => {
    const from = (starts[i]! / total) * 360 + gap;
    const to = ((starts[i]! + s.share) / total) * 360 - gap;
    return { ...s, d: to - from >= 359.9 ? null : arc(from, Math.max(from + 0.5, to)) };
  });
}

type Props = {
  data?: CategoryShares;
  // a legend row opens that category's spending
  onCategory?: (id: number) => void;
};

// Where the month's money went: a ring of the top categories and the rest
// (Figma: Аналітика › Витрати за категоріями)
export function CategoryDonut({ data, onCategory }: Props) {
  const { c, dark } = useTheme();
  const mask = useMask();
  const slices = data ? slicesOf(data, c) : [];

  const arcs = arcsOf(slices);

  return (
    <Glass contentStyle={styles.card}>
      <Text variant="labelCaps" tone="ghost">
        Витрати за категоріями
      </Text>
      {!data ? (
        <ActivityIndicator style={styles.loading} />
      ) : slices.length === 0 ? (
        <Text tone="faint" style={styles.empty}>
          Цього місяця витрат ще немає
        </Text>
      ) : (
        <View style={styles.body}>
          <View style={styles.ring}>
            <Svg width={SIZE} height={SIZE}>
              <Circle
                cx={SIZE / 2}
                cy={SIZE / 2}
                r={(SIZE - STROKE) / 2}
                stroke={withAlpha(c.shade, dark ? 0.12 : 0.07)}
                strokeWidth={STROKE}
                fill="none"
              />
              {arcs.map((a) =>
                a.d ? (
                  <Path key={a.key} d={a.d} stroke={a.color} strokeWidth={STROKE} fill="none" />
                ) : (
                  <Circle
                    key={a.key}
                    cx={SIZE / 2}
                    cy={SIZE / 2}
                    r={(SIZE - STROKE) / 2}
                    stroke={a.color}
                    strokeWidth={STROKE}
                    fill="none"
                  />
                ),
              )}
            </Svg>
            <View style={styles.center} pointerEvents="none">
              <Text style={styles.total} numberOfLines={1} adjustsFontSizeToFit>
                {mask(formatMoney(data.total, undefined, { cents: false }))}
              </Text>
            </View>
          </View>
          <View style={styles.legend}>
            {slices.map((s) => (
              <Pressable
                key={s.key}
                accessibilityRole={s.categoryId && onCategory ? 'button' : undefined}
                accessibilityLabel={`${s.name}, ${Math.round(s.share)}%`}
                disabled={!s.categoryId || !onCategory}
                onPress={() => s.categoryId && onCategory?.(s.categoryId)}
                style={({ pressed }) => [styles.row, pressed && styles.pressed]}
              >
                <View style={[styles.dot, { backgroundColor: s.color }]} />
                <Text style={styles.name} numberOfLines={1}>
                  {s.name}
                </Text>
                <Text style={styles.share}>{Math.round(s.share)}%</Text>
              </Pressable>
            ))}
          </View>
        </View>
      )}
    </Glass>
  );
}

const styles = StyleSheet.create({
  card: { paddingTop: 14, paddingHorizontal: 16, paddingBottom: 14, gap: 12 },
  loading: { marginVertical: 40 },
  empty: { paddingVertical: 20, textAlign: 'center' },
  body: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  ring: { width: SIZE, height: SIZE },
  center: { ...StyleSheet.absoluteFill, alignItems: 'center', justifyContent: 'center', paddingHorizontal: STROKE + 6 },
  total: { fontFamily: FONT.ui.bold, fontSize: 14, fontVariant: ['tabular-nums'] },
  legend: { flex: 1, gap: 6 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 1 },
  pressed: { opacity: 0.6 },
  dot: { width: 9, height: 9, borderRadius: 3 },
  name: { flex: 1, fontFamily: FONT.ui.medium, fontSize: 12.5 },
  share: { fontFamily: FONT.ui.semiBold, fontSize: 12.5, fontVariant: ['tabular-nums'] },
});
