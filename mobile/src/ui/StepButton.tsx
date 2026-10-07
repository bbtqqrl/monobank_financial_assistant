import { Pressable, StyleSheet } from 'react-native';

import { useTheme, whiteAlpha, withAlpha } from '@/theme';
import { Icon } from '@/ui/icons/Icon';

type Props = {
  dir: 'prev' | 'next';
  label: string;
  onPress: () => void;
  disabled?: boolean;
};

// Small glass arrow for stepping months or years
export function StepButton({ dir, label, onPress, disabled = false }: Props) {
  const { c, dark } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled }}
      disabled={disabled}
      hitSlop={8}
      onPress={onPress}
      style={({ pressed }) => [
        styles.step,
        {
          backgroundColor: withAlpha(c.white, whiteAlpha(0.6, dark)),
          borderColor: withAlpha(c.white, whiteAlpha(0.7, dark)),
        },
        pressed && styles.pressed,
      ]}
    >
      <Icon name={dir === 'prev' ? 'chevronLeft' : 'chevronRight'} size={16} color={disabled ? c.ghost : c.inkSoft} weight={1.9} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  // Figma: 30 / r10
  step: { width: 30, height: 30, borderRadius: 10, borderWidth: 1, alignItems: 'center', justifyContent: 'center' },
  pressed: { opacity: 0.6 },
});
