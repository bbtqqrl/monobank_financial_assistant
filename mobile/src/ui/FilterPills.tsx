import { Pressable, StyleSheet, View } from 'react-native';

import { FONT } from '@/lib/fonts';
import { useTheme, whiteAlpha, withAlpha } from '@/theme';
import { Text } from '@/ui/Text';

type Option<K extends string> = { key: K; label: string };

type Props<K extends string> = {
  options: Option<K>[];
  value: K;
  onChange: (key: K) => void;
};

// Row of filter pills, the active one is filled like the primary button
export function FilterPills<K extends string>({ options, value, onChange }: Props<K>) {
  const { c, dark } = useTheme();

  const activeFill = dark
    ? { backgroundColor: c.accentFill }
    : { experimental_backgroundImage: `linear-gradient(150deg, ${c.cardA}, ${c.cardB})` };
  const active = [activeFill, { boxShadow: `0 8px 18px -8px ${withAlpha(c.shadow, 0.7)}` }];
  const idle = {
    backgroundColor: withAlpha(c.white, whiteAlpha(0.5, dark)),
    borderColor: withAlpha(c.white, whiteAlpha(0.7, dark)),
    borderWidth: 1,
  };

  return (
    <View style={styles.row} accessibilityRole="tablist">
      {options.map((o) => {
        const on = o.key === value;
        return (
          <Pressable
            key={o.key}
            accessibilityRole="tab"
            accessibilityState={{ selected: on }}
            onPress={() => onChange(o.key)}
            style={({ pressed }) => [styles.pill, on ? active : idle, pressed && !on && styles.pressed]}
          >
            <Text
              variant="body"
              style={[styles.label, on ? styles.labelOn : null, { color: on ? c.onPrimary : c.category.neutral }]}
            >
              {o.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 6 },
  pill: { height: 34, borderRadius: 12, paddingHorizontal: 13, alignItems: 'center', justifyContent: 'center' },
  pressed: { opacity: 0.6 },
  label: { fontSize: 13 },
  labelOn: { fontFamily: FONT.ui.semiBold },
});
