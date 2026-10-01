import { ActivityIndicator, Pressable, StyleSheet } from 'react-native';

import { useTheme, whiteAlpha, withAlpha } from '@/theme';
import { Text } from '@/ui/Text';

type Props = {
  label: string;
  onPress?: () => void;
  // primary: ink (accent in dark), secondary: light glass
  kind?: 'primary' | 'secondary';
  loading?: boolean;
  disabled?: boolean;
};

export function Button({ label, onPress, kind = 'primary', loading = false, disabled = false }: Props) {
  const { c, dark } = useTheme();
  const primary = kind === 'primary';
  const fill = primary
    ? dark
      ? { backgroundColor: c.accentFill }
      : { experimental_backgroundImage: `linear-gradient(150deg, ${c.cardA}, ${c.cardB})` }
    : { backgroundColor: withAlpha(c.white, whiteAlpha(0.72, dark)) };

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: disabled || loading, busy: loading }}
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        fill,
        primary
          ? { borderColor: withAlpha(c.white, 0.12), boxShadow: `0 16px 32px -14px ${withAlpha(c.shadow, 0.8)}` }
          : { borderColor: withAlpha(c.shade, 0.08) },
        (pressed || disabled) && styles.dim,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={primary ? c.onPrimary : c.ink} />
      ) : (
        <Text variant="button" tone={primary ? 'onPrimary' : 'ink'}>
          {label}
        </Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    height: 54,
    borderRadius: 19,
    borderWidth: 1,
    paddingHorizontal: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dim: { opacity: 0.6 },
});
