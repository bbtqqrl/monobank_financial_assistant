import { Pressable, StyleSheet, View } from 'react-native';

import { useTheme, withAlpha } from '@/theme';
import { Icon } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

type Props = {
  title: string;
  subtitle?: string;
  // without it the title sits in the middle; the sheet still closes with a swipe
  onClose?: () => void;
};

// Title and a line under it, with a close button on the right
export function SheetHeader({ title, subtitle, onClose }: Props) {
  const { c } = useTheme();

  return (
    <View style={styles.head}>
      <View style={[styles.titles, !onClose && styles.centered]}>
        <Text variant="screenTitle">{title}</Text>
        {subtitle ? (
          <Text variant="rowCaption" tone="faint" style={styles.subtitle} numberOfLines={1}>
            {subtitle}
          </Text>
        ) : null}
      </View>
      {onClose ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Закрити"
          hitSlop={8}
          onPress={onClose}
          style={[styles.close, { backgroundColor: withAlpha(c.shade, 0.06) }]}
        >
          <Icon name="close" size={18} color={c.inkSoft} weight={1.9} />
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  head: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
  titles: { gap: 3, flexShrink: 1 },
  centered: { flex: 1, alignItems: 'center' },
  subtitle: { fontSize: 12.5 },
  close: { width: 38, height: 38, borderRadius: 13, alignItems: 'center', justifyContent: 'center' },
});
