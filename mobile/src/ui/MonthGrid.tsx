import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { useTheme, whiteAlpha, withAlpha } from '@/theme';
import { StepButton } from '@/ui/StepButton';
import { Text } from '@/ui/Text';

const MONTHS = ['Січ', 'Лют', 'Бер', 'Кві', 'Тра', 'Чер', 'Лип', 'Сер', 'Вер', 'Жов', 'Лис', 'Гру'];

type Props = {
  // the picked month, if any
  year?: number;
  month?: number;
  onPick: (year: number, month: number) => void;
  // months with no transactions can't be picked
  isEnabled?: (m: { year: number; month: number }) => boolean;
  // no years before this one
  minYear?: number;
};

// Year switcher and a 4×3 grid of months; future months are disabled
export function MonthGrid({ year, month, onPick, isEnabled, minYear }: Props) {
  const { c, dark } = useTheme();
  const now = new Date();
  const [shown, setShown] = useState(year ?? now.getFullYear());

  return (
    <View style={styles.box}>
      <View style={styles.years}>
        <StepButton
          dir="prev"
          label="Попередній рік"
          onPress={() => setShown(shown - 1)}
          disabled={minYear !== undefined && shown <= minYear}
        />
        <Text variant="screenTitle" style={styles.year}>
          {shown}
        </Text>
        <StepButton
          dir="next"
          label="Наступний рік"
          onPress={() => setShown(shown + 1)}
          disabled={shown >= now.getFullYear()}
        />
      </View>

      <View style={styles.grid}>
        {[0, 1, 2, 3].map((row) => (
          <View key={row} style={styles.row}>
            {MONTHS.slice(row * 3, row * 3 + 3).map((name, k) => {
              const i = row * 3 + k;
              const selected = shown === year && i === month;
              const future = shown > now.getFullYear() || (shown === now.getFullYear() && i > now.getMonth());
              const off = future || !(isEnabled?.({ year: shown, month: i }) ?? true);
              return (
                <Pressable
                  key={name}
                  accessibilityRole="button"
                  accessibilityState={{ selected, disabled: off }}
                  disabled={off}
                  onPress={() => onPick(shown, i)}
                  style={({ pressed }) => [
                    styles.tile,
                    selected
                      ? [
                          dark
                            ? { backgroundColor: c.accentFill }
                            : { experimental_backgroundImage: `linear-gradient(150deg, ${c.cardA}, ${c.cardB})` },
                          { boxShadow: `0 8px 18px -8px ${withAlpha(c.shadow, 0.6)}` },
                        ]
                      : {
                          backgroundColor: withAlpha(c.white, whiteAlpha(off ? 0.5 : 0.72, dark)),
                          borderColor: withAlpha(c.shade, 0.07),
                          borderWidth: 1,
                        },
                    pressed && styles.pressed,
                  ]}
                >
                  <Text
                    variant="bodyStrong"
                    style={[styles.name, { color: selected ? c.onPrimary : off ? c.ghost : c.ink }]}
                  >
                    {name}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  box: { gap: 14 },
  years: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  year: { fontSize: 18 },
  // three per row, Figma: 58 high, r15, 9 apart
  grid: { gap: 9 },
  row: { flexDirection: 'row', gap: 9 },
  tile: { flex: 1, height: 58, borderRadius: 15, alignItems: 'center', justifyContent: 'center' },
  name: { fontSize: 14 },
  pressed: { opacity: 0.7 },
});
