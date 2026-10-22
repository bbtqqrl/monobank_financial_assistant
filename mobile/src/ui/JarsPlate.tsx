import { Pressable, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { jarProgress, type Jar } from '@/api/jars';
import { FONT } from '@/lib/fonts';
import { formatMoney, UAH } from '@/lib/money';
import { plural } from '@/lib/plural';
import { useMask } from '@/lib/privacy';
import { TEXT, useTheme, withAlpha } from '@/theme';
import { Text } from '@/ui/Text';

// the plate has room for this many jars, the rest is "ще N"
const SHOWN = 2;
const PLATE_INK = '#1A1714';

// The ones worth a glance first: goals closest to done, then the reached
// ones, then jars without a goal by how much is in them
function pick(jars: Jar[]) {
  const rank = (j: Jar) => {
    const p = jarProgress(j);
    if (p === null) return 2;
    return p >= 1 ? 1 : 0;
  };
  return [...jars].sort(
    (a, b) => rank(a) - rank(b) || (jarProgress(b) ?? 0) - (jarProgress(a) ?? 0) || b.balance - a.balance,
  );
}

type Props = {
  jars: Jar[];
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
};

// The last plate in the balance carousel: every jar together, green so it
// never reads as one more card (cards are money to spend, jars money saved)
export function JarsPlate({ jars, onPress, style }: Props) {
  const { c, dark } = useTheme();
  const mask = useMask();
  const green = c.category.green;
  const ink = dark ? c.cream : PLATE_INK;
  const soft = (a: number) => withAlpha(ink, a);

  const total = jars.filter((j) => j.currency_code === UAH).reduce((s, j) => s + j.balance, 0);
  // jars in other currencies aren't added up into hryvnias, just listed
  const others = jars.filter((j) => j.currency_code !== UAH);
  const shown = pick(jars).slice(0, SHOWN);
  const more = jars.length - shown.length;

  const background = dark
    ? 'linear-gradient(152deg, #1C3A2D 0%, #0F2119 100%)'
    : `linear-gradient(152deg, #E6F2EB 0%, #C7E2D3 100%)`;
  const shadow = [
    `0 1px 2px ${withAlpha(c.shadow, 0.2)}`,
    `0 12px 26px -14px ${withAlpha(c.shadow, 0.5)}`,
    `0 30px 44px -24px ${withAlpha(green, 0.45)}`,
  ].join(', ');

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Банки: ${plural(jars.length, ['банка', 'банки', 'банок'])}, ${mask(formatMoney(total, UAH))}`}
      accessibilityHint="Відкрити всі банки"
      onPress={onPress}
      style={({ pressed }) => [pressed && styles.held, style]}
    >
      {/* the shadow comes from an underlay, as on the card plates */}
      <View style={[styles.underlay, { backgroundColor: dark ? '#0F2119' : '#C7E2D3', boxShadow: shadow }]} />
      <View style={[styles.plate, { experimental_backgroundImage: background }]}>
        <View style={styles.left}>
          <Text variant="labelCaps" style={[styles.label, { color: soft(0.55) }]}>
            Банки
          </Text>
          <Text maxFontSizeMultiplier={1.3} numberOfLines={1} style={[styles.total, { color: ink }]}>
            {mask(formatMoney(total, UAH, { cents: false }))}
          </Text>
          <Text variant="rowCaption" numberOfLines={1} style={{ color: soft(0.55) }}>
            {[
              plural(jars.length, ['банка', 'банки', 'банок']),
              ...others.map((j) => `+${mask(formatMoney(j.balance, j.currency_code, { cents: false }))}`),
            ].join(' · ')}
          </Text>
        </View>

        <View style={styles.right}>
          {shown.map((j) => {
            const p = jarProgress(j);
            return (
              <View key={j.id} style={styles.jar}>
                <View style={styles.jarHead}>
                  <Text numberOfLines={1} style={[styles.jarName, { color: soft(0.85) }]}>
                    {j.title}
                  </Text>
                  <Text style={[styles.jarValue, { color: soft(0.6) }]}>
                    {p === null ? mask(formatMoney(j.balance, j.currency_code, { cents: false })) : `${Math.floor(p * 100)}%`}
                  </Text>
                </View>
                {p !== null ? (
                  <View style={[styles.track, { backgroundColor: withAlpha(green, dark ? 0.25 : 0.18) }]}>
                    <View style={[styles.fill, { width: `${p * 100}%`, backgroundColor: green }]} />
                  </View>
                ) : null}
              </View>
            );
          })}
          {more > 0 ? (
            <Text variant="rowCaption" style={[styles.more, { color: soft(0.5) }]}>
              ще {plural(more, ['банка', 'банки', 'банок'])}
            </Text>
          ) : null}
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  held: { transform: [{ scale: 0.985 }] },
  underlay: { position: 'absolute', top: 1, left: 1, right: 1, bottom: 1, borderRadius: 25, borderCurve: 'continuous' },
  plate: {
    borderRadius: 26,
    borderCurve: 'continuous',
    paddingVertical: 15,
    paddingHorizontal: 17,
    overflow: 'hidden',
    flexDirection: 'row',
    gap: 16,
    // as tall as a card plate, so the carousel doesn't jump
    minHeight: 123,
  },
  left: { flex: 1, minWidth: 0, justifyContent: 'space-between' },
  label: { letterSpacing: 0.69 },
  total: { ...TEXT.amountXl, fontSize: 28, lineHeight: 34, letterSpacing: -0.6 },
  right: { flex: 1.15, justifyContent: 'center', gap: 9 },
  jar: { gap: 4 },
  jarHead: { flexDirection: 'row', alignItems: 'baseline', gap: 6 },
  jarName: { flex: 1, fontFamily: FONT.ui.semiBold, fontSize: 12.5 },
  jarValue: { fontFamily: FONT.ui.semiBold, fontSize: 12, fontVariant: ['tabular-nums'] },
  track: { height: 5, borderRadius: 3, overflow: 'hidden' },
  fill: { height: 5, borderRadius: 3 },
  more: { fontSize: 12 },
});
