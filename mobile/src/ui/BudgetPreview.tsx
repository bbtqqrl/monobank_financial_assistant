import type { RefObject } from 'react';
import { Pressable, StyleSheet, TextInput } from 'react-native';
import Animated, { FadeIn, FadeOut } from 'react-native-reanimated';

import type { CategoryLook } from '@/lib/categories';
import { useTheme, withAlpha } from '@/theme';
import { CategoryChip } from '@/ui/CategoryChip';
import { Glass } from '@/ui/Glass';
import { LimitField } from '@/ui/LimitField';
import { Text } from '@/ui/Text';

type Props = {
  // null until a category is picked
  look: CategoryLook | null;
  name: string | null;
  // the chip opens the full list; a saved budget keeps its category
  onCategoryPress?: () => void;
  amountText: string;
  onAmountText: (text: string) => void;
  caption: string;
  inputRef?: RefObject<TextInput | null>;
};

// The budget being set, like the new transaction one: chip, category, the
// limit typed in place
export function BudgetPreview({ look, name, onCategoryPress, amountText, onAmountText, caption, inputRef }: Props) {
  const { c } = useTheme();
  const tint = look ? c.category[look.color] : c.accent;
  const chip = <CategoryChip {...(look ?? { icon: 'plus', color: 'neutral' })} size={62} radius={22} />;

  return (
    <Glass radius={26} contentStyle={styles.card}>
      <Animated.View
        key={tint}
        entering={FadeIn.duration(220)}
        exiting={FadeOut.duration(220)}
        pointerEvents="none"
        style={[
          StyleSheet.absoluteFill,
          {
            experimental_backgroundImage: `radial-gradient(110% 80% at 50% 0%, ${withAlpha(tint, 0.22)} 0%, ${withAlpha(tint, 0)} 72%)`,
          },
        ]}
      />

      {onCategoryPress ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={look ? 'Змінити категорію' : 'Обрати категорію'}
          onPress={onCategoryPress}
          style={({ pressed }) => pressed && styles.pressed}
        >
          {chip}
        </Pressable>
      ) : (
        chip
      )}

      <Text variant="bodyStrong" tone={name ? 'ink' : 'faint'} style={styles.name} numberOfLines={1}>
        {name ?? 'Обери категорію'}
      </Text>

      <LimitField text={amountText} onText={onAmountText} inputRef={inputRef} />

      <Text variant="rowCaption" tone="faint" style={styles.caption} numberOfLines={1}>
        {caption}
      </Text>
    </Glass>
  );
}

const styles = StyleSheet.create({
  card: { alignItems: 'center', gap: 10, paddingTop: 18, paddingBottom: 16, paddingHorizontal: 16 },
  name: { marginTop: 2, fontSize: 16, lineHeight: 21 },
  pressed: { opacity: 0.6 },
  caption: { fontSize: 12.5 },
});
