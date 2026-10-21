import { Pressable, StyleSheet, View } from 'react-native';

import { jarProgress, type Jar } from '@/api/jars';
import { FONT } from '@/lib/fonts';
import { formatMoney } from '@/lib/money';
import { useMask } from '@/lib/privacy';
import { useTheme, withAlpha } from '@/theme';
import { Icon } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

// The green jar tile, small in the list and big on the jar's own screen
export function JarTile({ size = 36 }: { size?: number }) {
  const { c } = useTheme();
  const green = c.category.green;
  return (
    <View
      style={[
        styles.tile,
        { width: size, height: size, borderRadius: size / 3, backgroundColor: withAlpha(green, 0.14) },
      ]}
    >
      <Icon name="jar" size={size * 0.47} color={green} weight={1.8} />
    </View>
  );
}

// One jar, laid out like a budget: name, a bar of how much is saved, what's
// left to the goal. A jar without a goal shows only what's in it.
export function JarRow({ jar, onPress }: { jar: Jar; onPress?: () => void }) {
  const { c, dark } = useTheme();
  const mask = useMask();
  const progress = jarProgress(jar);
  const money = (v: number) => mask(formatMoney(v, jar.currency_code, { cents: false }));
  const reached = progress === 1;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityHint="Відкрити банку"
      onPress={onPress}
      style={({ pressed }) => [styles.row, pressed && styles.pressed]}
    >
      <JarTile />
      <View style={styles.text}>
        <Text variant="bodyStrong" numberOfLines={1}>
          {jar.title}
        </Text>
        {progress !== null ? (
          <View style={[styles.track, { backgroundColor: withAlpha(c.shade, dark ? 0.12 : 0.08) }]}>
            <View style={[styles.fill, { width: `${progress * 100}%`, backgroundColor: c.category.green }]} />
          </View>
        ) : null}
        <View style={styles.bottom}>
          <Text
            variant="rowCaption"
            style={[reached && styles.reached, { color: reached ? c.positive : c.faint }]}
          >
            {progress === null
              ? 'Без цілі'
              : reached
                ? 'Ціль зібрано'
                : `До цілі ${money((jar.goal ?? 0) - jar.balance)}`}
          </Text>
          <Text variant="rowCaption" tone="muted" style={styles.sum}>
            {progress === null ? money(jar.balance) : `${money(jar.balance)} з ${money(jar.goal ?? 0)}`}
          </Text>
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  tile: { alignItems: 'center', justifyContent: 'center', borderCurve: 'continuous' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 9 },
  pressed: { opacity: 0.6 },
  text: { flex: 1, gap: 6 },
  track: { height: 6, borderRadius: 3, overflow: 'hidden' },
  fill: { height: 6, borderRadius: 3 },
  bottom: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'baseline', columnGap: 8, rowGap: 2 },
  reached: { fontFamily: FONT.ui.semiBold },
  sum: { fontVariant: ['tabular-nums'] },
});
