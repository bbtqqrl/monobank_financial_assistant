import type { ReactNode } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { FONT } from '@/lib/fonts';
import { useTheme, whiteAlpha, withAlpha } from '@/theme';
import { Icon, type IconName } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

type Props = {
  // left out for an icon-only pill, which then needs accessibilityLabel
  label?: string;
  accessibilityLabel?: string;
  active?: boolean;
  icon?: IconName;
  onPress?: () => void;
  // small cross inside an active pill, e.g. to drop a custom period
  onClear?: () => void;
  role?: 'tab' | 'button';
};

// Filter pill: light glass, or filled like the primary button when active
export function Pill({ label, accessibilityLabel, active = false, icon, onPress, onClear, role = 'button' }: Props) {
  const { c, dark } = useTheme();
  const tone = active ? c.onPrimary : c.category.neutral;

  const look = active
    ? [
        dark
          ? { backgroundColor: c.accentFill }
          : { experimental_backgroundImage: `linear-gradient(150deg, ${c.cardA}, ${c.cardB})` },
        { boxShadow: `0 8px 18px -8px ${withAlpha(c.shadow, 0.7)}` },
      ]
    : {
        backgroundColor: withAlpha(c.white, whiteAlpha(0.5, dark)),
        borderColor: withAlpha(c.white, whiteAlpha(0.7, dark)),
        borderWidth: 1,
      };

  return (
    <Pressable
      accessibilityRole={role}
      accessibilityLabel={accessibilityLabel}
      accessibilityState={{ selected: active }}
      onPress={onPress}
      style={({ pressed }) => [
        styles.pill,
        !label && styles.square,
        onClear && styles.clearable,
        look,
        pressed && !active && styles.pressed,
      ]}
    >
      {icon ? <Icon name={icon} size={label ? 14 : 17} color={tone} weight={1.9} /> : null}
      {label ? (
        <Text variant="body" style={[styles.label, active && styles.labelOn, { color: tone }]}>
          {label}
        </Text>
      ) : null}
      {onClear ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Прибрати"
          hitSlop={10}
          onPress={onClear}
          style={[styles.clear, { backgroundColor: withAlpha(c.white, 0.22) }]}
        >
          <Icon name="close" size={11} color={c.onPrimary} weight={2.4} />
        </Pressable>
      ) : null}
    </Pressable>
  );
}

export function PillRow({ children, wrap = false }: { children: ReactNode; wrap?: boolean }) {
  return <View style={[styles.row, wrap && styles.wrap]}>{children}</View>;
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 6 },
  wrap: { flexWrap: 'wrap', gap: 7 },
  pill: {
    height: 34,
    borderRadius: 12,
    paddingHorizontal: 13,
    flexDirection: 'row',
    gap: 6,
    alignItems: 'center',
    justifyContent: 'center',
  },
  square: { width: 34, paddingHorizontal: 0 },
  clearable: { paddingRight: 8 },
  pressed: { opacity: 0.6 },
  label: { fontSize: 13 },
  labelOn: { fontFamily: FONT.ui.semiBold },
  clear: { width: 18, height: 18, borderRadius: 9, alignItems: 'center', justifyContent: 'center' },
});
