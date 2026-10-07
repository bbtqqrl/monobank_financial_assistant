import { Pressable, StyleSheet, View } from 'react-native';

import type { CategoryLook } from '@/lib/categories';
import { formatMoney } from '@/lib/money';
import { useTheme } from '@/theme';
import { CategoryChip } from '@/ui/CategoryChip';
import { Text } from '@/ui/Text';

type Props = {
  look: CategoryLook;
  title: string;
  // category name
  caption: string;
  // minor units, negative = spent
  amount: number;
  currency: number;
  // "10:32", "Вчора", "18 травня"
  when: string;
  // the purchase itself when it was in another currency, e.g. 9,00 zł paid from a UAH card
  original?: { amount: number; currency: number };
  // compact rows on Overview use a 38pt chip
  compact?: boolean;
  onPress?: () => void;
};

// Transaction row: category chip · merchant and category · amount and time
export function TxRow({ look, title, caption, amount, currency, when, original, compact = false, onPress }: Props) {
  const { c } = useTheme();
  const income = amount > 0;
  const sub = original ? `${formatMoney(original.amount, original.currency, { sign: 'never' })} · ${when}` : when;

  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.row, compact ? styles.compact : styles.regular, pressed && styles.pressed]}
    >
      <CategoryChip {...look} size={compact ? 38 : 40} />
      <View style={styles.middle}>
        <Text variant="rowTitle" numberOfLines={1}>
          {title}
        </Text>
        <Text variant="rowCaption" tone="faint" numberOfLines={1}>
          {caption}
        </Text>
      </View>
      <View style={styles.right}>
        <Text variant="rowAmount" style={income && { color: c.category.green }}>
          {formatMoney(amount, currency, { sign: income ? 'always' : 'auto' })}
        </Text>
        <Text variant="rowCaption" tone="faint" style={styles.when}>
          {sub}
        </Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  compact: { paddingVertical: 6 },
  regular: { paddingVertical: 10 },
  pressed: { opacity: 0.6 },
  middle: { flex: 1, gap: 2 },
  right: { alignItems: 'flex-end', gap: 2 },
  when: { fontSize: 11.5 },
});
