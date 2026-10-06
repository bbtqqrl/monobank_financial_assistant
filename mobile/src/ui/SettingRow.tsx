import { Pressable, StyleSheet, View } from 'react-native';

import { useTheme, withAlpha } from '@/theme';
import { Icon, type IconName } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

type Props = {
  icon: IconName;
  label: string;
  value?: string;
  accent?: boolean;
  onPress?: () => void;
};

export function SettingRow({ icon, label, value, accent = false, onPress }: Props) {
  const { c } = useTheme();
  const tone = accent ? c.accent : c.inkSoft;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={value ? `${label}: ${value}` : label}
      onPress={onPress}
      style={({ pressed }) => [styles.row, pressed && styles.pressed]}
    >
      <View style={[styles.tile, { backgroundColor: withAlpha(accent ? c.accent : c.shade, accent ? 0.16 : 0.07) }]}>
        <Icon name={icon} size={17} color={tone} weight={1.8} />
      </View>
      <Text style={styles.label}>{label}</Text>
      {value ? (
        <Text variant="bodyStrong" tone="faint" style={styles.value}>
          {value}
        </Text>
      ) : null}
      <Icon name="chevronRight" size={18} color={c.ghost} weight={1.9} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10 },
  pressed: { opacity: 0.6 },
  tile: { width: 36, height: 36, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  label: { flex: 1, fontSize: 14, lineHeight: 19 },
  value: { fontSize: 13 },
});
