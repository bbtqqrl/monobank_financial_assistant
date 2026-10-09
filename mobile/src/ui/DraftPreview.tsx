import { useEffect } from 'react';
import { Pressable, StyleSheet, TextInput, View } from 'react-native';
import Animated, {
  FadeIn,
  FadeOut,
  interpolateColor,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';

import type { CategoryLook } from '@/lib/categories';
import type { DraftDirection } from '@/lib/draft';
import { FONT } from '@/lib/fonts';
import { currencySymbol } from '@/lib/money';
import { useTheme, withAlpha } from '@/theme';
import { CategoryChip } from '@/ui/CategoryChip';
import { Glass } from '@/ui/Glass';
import { Segmented } from '@/ui/Segmented';
import { Text } from '@/ui/Text';

type Props = {
  direction: DraftDirection;
  onDirection: (direction: DraftDirection) => void;
  // null until a category is picked
  look: CategoryLook | null;
  // the big chip opens the full category list
  onCategoryPress: () => void;
  amountText: string;
  onAmountText: (text: string) => void;
  currency: number;
  description: string;
  onDescription: (text: string) => void;
  // shown while the description is empty
  descriptionHint: string;
  // "Продукти · Готівка · Сьогодні"
  summary: string;
};

// what can be typed into the amount, the currency's decimals are checked later
const AMOUNT_TYPING = /^\d{0,9}(?:[.,]\d{0,2})?$/;

// "12500,5" → "12 500,5" while typing
const groupThousands = (text: string) => {
  const [whole = '', fraction] = text.split(/[.,]/);
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return fraction === undefined ? grouped : `${grouped},${fraction}`;
};

// The transaction being made, laid out like its details screen: chip, name,
// amount. Name and amount are typed in place.
export function DraftPreview({
  direction,
  onDirection,
  look,
  onCategoryPress,
  amountText,
  onAmountText,
  currency,
  description,
  onDescription,
  descriptionHint,
  summary,
}: Props) {
  const { c } = useTheme();
  const income = direction === 'income';
  const tint = look ? c.category[look.color] : income ? c.category.green : c.accent;

  // the amount turns green and back instead of flipping
  const tone = useSharedValue(income ? 1 : 0);
  useEffect(() => {
    tone.set(withTiming(income ? 1 : 0, { duration: 200 }));
  }, [income, tone]);
  const amountTone = useAnimatedStyle(() => ({
    color: interpolateColor(tone.get(), [0, 1], [c.ink, c.category.green]),
  }));

  return (
    <Glass radius={26} contentStyle={styles.card}>
      {/* the glow fades from one category's colour to the next */}
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
      <Segmented
        options={[
          { key: 'expense', label: 'Витрата' },
          { key: 'income', label: 'Дохід', tint: c.category.green },
        ]}
        value={direction}
        onChange={onDirection}
      />

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={look ? 'Змінити категорію' : 'Обрати категорію'}
        onPress={onCategoryPress}
        style={({ pressed }) => pressed && styles.pressed}
      >
        <CategoryChip {...(look ?? { icon: 'plus', color: 'neutral' })} size={62} radius={22} />
      </Pressable>

      <TextInput
        value={description}
        onChangeText={onDescription}
        placeholder={descriptionHint}
        placeholderTextColor={c.ghost}
        selectionColor={c.accent}
        maxLength={500}
        returnKeyType="done"
        maxFontSizeMultiplier={1.3}
        accessibilityLabel="Опис"
        style={[styles.description, { color: c.ink }]}
      />

      {/* Drawn as text with grouped thousands; an invisible input on top takes
          the typing (a self-sizing input leaves caret marks behind). */}
      <View style={styles.amount}>
        <Animated.Text style={[styles.amountText, amountTone]}>{income ? '+' : '−'}</Animated.Text>
        {amountText ? (
          <Animated.Text style={[styles.amountText, amountTone]}>{groupThousands(amountText)}</Animated.Text>
        ) : (
          <Text style={[styles.amountText, { color: c.ghost }]}>0</Text>
        )}
        <Text style={[styles.amountText, { color: c.ghost }]}>{currencySymbol(currency)}</Text>
        <TextInput
          value={amountText}
          onChangeText={(next) => {
            if (AMOUNT_TYPING.test(next)) onAmountText(next);
          }}
          keyboardType="decimal-pad"
          autoFocus
          caretHidden
          contextMenuHidden
          accessibilityLabel="Сума"
          style={[StyleSheet.absoluteFill, styles.hidden]}
        />
      </View>

      <Text variant="rowCaption" tone="faint" style={styles.summary} numberOfLines={1}>
        {summary}
      </Text>
    </Glass>
  );
}

const styles = StyleSheet.create({
  card: { alignItems: 'center', gap: 10, paddingTop: 14, paddingBottom: 16, paddingHorizontal: 16 },
  description: {
    alignSelf: 'stretch',
    marginTop: 2,
    padding: 0,
    textAlign: 'center',
    fontFamily: FONT.ui.semiBold,
    fontSize: 16,
    lineHeight: 21,
  },
  amount: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  amountText: { fontFamily: FONT.ui.bold, fontSize: 40, lineHeight: 48, letterSpacing: -0.5 },
  hidden: { color: 'transparent' },
  pressed: { opacity: 0.6 },
  summary: { fontSize: 12.5 },
});
