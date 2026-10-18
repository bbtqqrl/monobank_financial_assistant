import { Pressable, StyleSheet, Switch, View } from 'react-native';

import { toggle } from '@/lib/haptics';
import { useTheme, withAlpha } from '@/theme';
import { Icon, type IconName } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

type Props = {
  icon: IconName;
  label: string;
  // a line under the label: what the switch does, or why it can't be turned on
  caption?: string;
  value: boolean;
  onChange: (on: boolean) => void;
  disabled?: boolean;
};

// A settings row with a switch, laid out like SettingRow; the whole row flips it
export function SwitchRow({ icon, label, caption, value, onChange, disabled = false }: Props) {
  const { c } = useTheme();
  const flip = (on: boolean) => {
    toggle();
    onChange(on);
  };

  return (
    <Pressable
      accessibilityRole="switch"
      accessibilityLabel={label}
      accessibilityState={{ checked: value, disabled }}
      disabled={disabled}
      onPress={() => flip(!value)}
      style={({ pressed }) => [styles.row, disabled && styles.dim, pressed && styles.pressed]}
    >
      <View style={[styles.tile, { backgroundColor: withAlpha(c.shade, 0.07) }]}>
        <Icon name={icon} size={17} color={c.inkSoft} weight={1.8} />
      </View>
      <View style={styles.text}>
        <Text style={styles.label}>{label}</Text>
        {caption ? (
          <Text variant="rowCaption" tone="faint">
            {caption}
          </Text>
        ) : null}
      </View>
      <Switch
        value={value}
        disabled={disabled}
        onValueChange={flip}
        trackColor={{ true: c.accent }}
        // the row speaks for it
        accessibilityElementsHidden
        importantForAccessibility="no"
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10 },
  dim: { opacity: 0.55 },
  pressed: { opacity: 0.7 },
  tile: { width: 36, height: 36, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  text: { flex: 1, gap: 2 },
  label: { fontSize: 14, lineHeight: 19 },
});
