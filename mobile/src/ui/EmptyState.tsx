import { StyleSheet, View } from 'react-native';

import { useTheme, withAlpha } from '@/theme';
import { Icon, type IconName } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

type Props = {
  icon: IconName;
  title: string;
  caption: string;
};

// Icon tile, title and a short explanation, centred
export function EmptyState({ icon, title, caption }: Props) {
  const { c, dark } = useTheme();

  return (
    <View style={styles.box}>
      <View style={[styles.tile, { backgroundColor: withAlpha(c.shade, dark ? 0.08 : 0.05) }]}>
        <Icon name={icon} size={28} color={c.ghost} />
      </View>
      <Text variant="bodyStrong" style={styles.title}>
        {title}
      </Text>
      <Text tone="faint" style={styles.caption}>
        {caption}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  box: { alignItems: 'center', gap: 12, paddingVertical: 46, paddingHorizontal: 20 },
  tile: { width: 64, height: 64, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 15, lineHeight: 20 },
  caption: { fontSize: 12.5, lineHeight: 17, textAlign: 'center', maxWidth: 250 },
});
