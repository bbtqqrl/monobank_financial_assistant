import { Pressable, StyleSheet, View } from 'react-native';

import { tap } from '@/lib/haptics';
import { useTheme } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Icon, type IconName } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

function Arrow({ icon, label, onPress }: { icon: IconName; label: string; onPress?: () => void }) {
  const { c } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={!onPress}
      hitSlop={6}
      onPress={() => {
        tap();
        onPress?.();
      }}
      style={({ pressed }) => [!onPress && styles.off, pressed && styles.pressed]}
    >
      <Glass radius={12} contentStyle={styles.arrow}>
        <Icon name={icon} size={17} color={c.inkSoft} weight={1.9} />
      </Glass>
    </Pressable>
  );
}

// "‹ Травень 2026 ›": no arrow forward past this month
export function MonthSwitcher({ title, onPrev, onNext }: { title: string; onPrev?: () => void; onNext?: () => void }) {
  return (
    <View style={styles.row}>
      <Arrow icon="chevronLeft" label="Попередній місяць" onPress={onPrev} />
      <Text variant="labelSection" style={styles.title} accessibilityRole="header">
        {title}
      </Text>
      <Arrow icon="chevronRight" label="Наступний місяць" onPress={onNext} />
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  title: { flex: 1, textAlign: 'center', fontSize: 15 },
  arrow: { width: 34, height: 34, alignItems: 'center', justifyContent: 'center' },
  off: { opacity: 0.35 },
  pressed: { opacity: 0.6 },
});
