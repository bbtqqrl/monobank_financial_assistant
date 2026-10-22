import { Pressable, StyleSheet, View } from 'react-native';

import { budgetRatio, type Budget } from '@/api/budgets';
import { categoryLook } from '@/lib/categories';
import { FONT } from '@/lib/fonts';
import { formatMoney } from '@/lib/money';
import { useMask } from '@/lib/privacy';
import { useTheme, withAlpha, type Colors } from '@/theme';
import { CategoryChip } from '@/ui/CategoryChip';
import { Text } from '@/ui/Text';

// past this share of the limit the bar turns amber
const NEAR = 0.9;

// the category's own colour, amber close to the limit, red past it
export function limitTone(ratio: number, own: string, c: Colors) {
  return ratio > 1 ? c.danger : ratio >= NEAR ? c.warning : own;
}

type Props = {
  budget: Budget;
  onPress?: () => void;
  // held: straight to changing the limit
  onLongPress?: () => void;
};

// as long as the balance card takes to open its settings
const HOLD_MS = 380;

// One category's limit: chip · name, a bar of how much is gone, what's left
export function BudgetRow({ budget, onPress, onLongPress }: Props) {
  const { c, dark } = useTheme();
  const mask = useMask();
  const look = categoryLook(budget.category.slug, -1);
  const ratio = budgetRatio(budget);
  const over = ratio > 1;
  const tone = limitTone(ratio, c.category[look.color], c);
  const left = budget.amount - budget.current_amount;
  const money = (v: number) => mask(formatMoney(v, undefined, { cents: false }));

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityHint="Відкрити бюджет"
      accessibilityActions={onLongPress ? [{ name: 'longpress', label: 'Змінити ліміт' }] : undefined}
      onAccessibilityAction={(e) => {
        if (e.nativeEvent.actionName === 'longpress') onLongPress?.();
      }}
      onPress={onPress}
      onLongPress={onLongPress}
      delayLongPress={HOLD_MS}
      style={({ pressed }) => [styles.row, pressed && styles.pressed]}
    >
      <CategoryChip {...look} size={36} radius={12} />
      <View style={styles.text}>
        <Text variant="bodyStrong" numberOfLines={1}>
          {budget.category.name}
        </Text>
        <View style={[styles.track, { backgroundColor: withAlpha(c.shade, dark ? 0.12 : 0.08) }]}>
          <View style={[styles.fill, { width: `${Math.min(ratio, 1) * 100}%`, backgroundColor: tone }]} />
        </View>
        <View style={styles.bottom}>
          <Text variant="rowCaption" style={[over && styles.overText, { color: over ? c.dangerText : c.faint }]}>
            {over ? `Перевищено на ${money(-left)}` : `Залишилось ${money(left)}`}
          </Text>
          <Text variant="rowCaption" tone="muted" style={styles.sum}>
            {money(budget.current_amount)} з {money(budget.amount)}
          </Text>
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 9 },
  pressed: { opacity: 0.6 },
  text: { flex: 1, gap: 6 },
  track: { height: 6, borderRadius: 3, overflow: 'hidden' },
  fill: { height: 6, borderRadius: 3 },
  // with large text the sum moves under what's left instead of running off the card
  bottom: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'baseline', columnGap: 8, rowGap: 2 },
  overText: { fontFamily: FONT.ui.semiBold },
  sum: { fontVariant: ['tabular-nums'] },
});
