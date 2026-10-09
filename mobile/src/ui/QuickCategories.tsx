import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import Animated from 'react-native-reanimated';

import type { CategoryBrief } from '@/api/categories';
import { categoryLook } from '@/lib/categories';
import { FONT } from '@/lib/fonts';
import { tap } from '@/lib/haptics';
import { useTheme, withAlpha } from '@/theme';
import { CategoryChip } from '@/ui/CategoryChip';
import { Icon } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';
import { useSelectRing } from '@/ui/useSelectRing';

type Props = {
  categories: CategoryBrief[];
  selectedId: number | null;
  income: boolean;
  onPick: (category: CategoryBrief) => void;
  // the full list
  onMore: () => void;
};

const CHIP = 50;
const ITEM = 78;
// roughly one letter of the label font
const LETTER = 6.6;

// iOS breaks a word that doesn't fit mid-way («Підприємниць-ка»), so an item
// with a long word gets wider instead
const itemWidth = (name: string) => Math.max(ITEM, Math.ceil(Math.max(...name.split(' ').map((w) => w.length)) * LETTER));

function Item({ category, selected, income, onPick }: {
  category: CategoryBrief;
  selected: boolean;
  income: boolean;
  onPick: (category: CategoryBrief) => void;
}) {
  const { c } = useTheme();
  const ring = useSelectRing(selected);

  return (
    <Pressable
      accessibilityRole="radio"
      accessibilityState={{ checked: selected }}
      accessibilityLabel={category.name}
      onPress={() => {
        if (selected) return;
        tap();
        onPick(category);
      }}
      style={({ pressed }) => [styles.item, { width: itemWidth(category.name) }, pressed && styles.pressed]}
    >
      <View style={styles.ringBox}>
        <Animated.View style={[styles.ring, { borderColor: c.accent }, ring]} />
        <CategoryChip {...categoryLook(category.slug, income ? 1 : -1)} size={CHIP} radius={17} />
      </View>
      <Text tone={selected ? 'ink' : 'muted'} numberOfLines={2} style={[styles.label, selected && styles.labelOn]}>
        {category.name}
      </Text>
    </Pressable>
  );
}

// Frequent categories as circles to pick in one tap, the rest behind «Усі»
export function QuickCategories({ categories, selectedId, income, onPick, onMore }: Props) {
  const { c } = useTheme();

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      // a tap picks right away, even while the amount keyboard is up
      keyboardShouldPersistTaps="handled"
      style={styles.scroll}
      contentContainerStyle={styles.row}
    >
      {categories.map((category) => (
        <Item
          key={category.id}
          category={category}
          selected={category.id === selectedId}
          income={income}
          onPick={onPick}
        />
      ))}
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Усі категорії"
        onPress={onMore}
        style={({ pressed }) => [styles.item, pressed && styles.pressed]}
      >
        <View style={styles.ringBox}>
          <View style={[styles.more, { backgroundColor: withAlpha(c.shade, 0.07) }]}>
            <Icon name="dots" size={22} color={c.inkSoft} weight={2.4} />
          </View>
        </View>
        <Text tone="muted" style={styles.label}>
          Усі
        </Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  // runs under the sheet's side padding, so circles scroll to the edge
  scroll: { marginHorizontal: -20 },
  row: { paddingHorizontal: 14, gap: 2 },
  item: { width: ITEM, alignItems: 'center', gap: 6 },
  pressed: { opacity: 0.6 },
  // 2pt of air and a 2pt ring around the chip
  ringBox: { padding: 4 },
  ring: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, borderWidth: 2, borderRadius: 21 },
  more: { width: CHIP, height: CHIP, borderRadius: 17, alignItems: 'center', justifyContent: 'center' },
  label: { fontFamily: FONT.ui.medium, fontSize: 11.5, lineHeight: 14, textAlign: 'center' },
  labelOn: { fontFamily: FONT.ui.semiBold },
});
