import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';

import type { CategoryLook } from '@/lib/categories';
import { FONT } from '@/lib/fonts';
import { useTheme, withAlpha } from '@/theme';
import { CategoryChip } from '@/ui/CategoryChip';
import { Icon } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

type Props = {
  look: CategoryLook;
  name: string;
  // the parent's name in search results
  caption?: string;
  selected: boolean;
  // being saved: a spinner in place of the radio
  busy?: boolean;
  onPress: () => void;
  // a parent with children gets a chevron to show them
  expanded?: boolean;
  onToggle?: () => void;
  // children sit indented with a smaller chip
  nested?: boolean;
};

// A row of the category list: chip · name · radio (Figma: ChangeCategory)
export function CategoryOption({
  look,
  name,
  caption,
  selected,
  busy = false,
  onPress,
  expanded,
  onToggle,
  nested = false,
}: Props) {
  const { c } = useTheme();

  return (
    <Pressable
      accessibilityRole="radio"
      accessibilityState={{ checked: selected, busy }}
      onPress={onPress}
      style={({ pressed }) => [
        styles.row,
        nested && styles.nested,
        selected && { backgroundColor: withAlpha(c.accent, 0.08), borderColor: withAlpha(c.accent, 0.22) },
        pressed && styles.pressed,
      ]}
    >
      <CategoryChip {...look} size={nested ? 30 : 34} radius={nested ? 10 : 11} />
      <View style={styles.text}>
        <Text variant="body" numberOfLines={1} style={[styles.name, selected && styles.nameOn]}>
          {name}
        </Text>
        {caption ? (
          <Text variant="rowCaption" tone="faint" numberOfLines={1}>
            {caption}
          </Text>
        ) : null}
      </View>
      {onToggle ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={expanded ? 'Сховати підкатегорії' : 'Показати підкатегорії'}
          hitSlop={8}
          onPress={onToggle}
          style={[styles.toggle, expanded && styles.toggleOpen]}
        >
          <Icon name="chevronDown" size={16} color={c.ghost} weight={2} />
        </Pressable>
      ) : null}
      {busy ? (
        <ActivityIndicator style={styles.spinner} color={c.accent} />
      ) : (
        <View
          style={[
            styles.radio,
            selected ? { backgroundColor: c.accent, borderColor: c.accent } : { borderColor: withAlpha(c.shade, 0.2) },
          ]}
        >
          {selected ? <Icon name="check" size={12} color={c.onPrimary} weight={3} /> : null}
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  // Figma: 48 high, 0 6, r14; the border is there so selecting doesn't shift it
  row: {
    minHeight: 48,
    paddingHorizontal: 6,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'transparent',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  nested: { minHeight: 44, marginLeft: 22 },
  pressed: { opacity: 0.6 },
  text: { flex: 1, gap: 1 },
  name: { fontSize: 14 },
  nameOn: { fontFamily: FONT.ui.semiBold },
  toggle: { width: 28, height: 28, borderRadius: 9, alignItems: 'center', justifyContent: 'center' },
  toggleOpen: { transform: [{ rotate: '180deg' }] },
  spinner: { width: 21, height: 21 },
  radio: { width: 21, height: 21, borderRadius: 11, borderWidth: 1.6, alignItems: 'center', justifyContent: 'center' },
});
