import { StyleSheet, View } from 'react-native';

import { IconButton, type IconButtonProps } from '@/ui/IconButton';
import { Text } from '@/ui/Text';

type Props = {
  title: string;
  left?: IconButtonProps;
  right?: IconButtonProps;
  // detail screens use a smaller title
  small?: boolean;
};

// Screen header: glass button · title · glass button. A missing button keeps
// its slot so the title stays centred.
export function Header({ title, left, right, small = false }: Props) {
  return (
    <View style={styles.row}>
      {left ? <IconButton {...left} /> : <View style={styles.slot} />}
      <Text
        variant="screenTitle"
        numberOfLines={1}
        accessibilityRole="header"
        style={[styles.title, small && styles.small]}
      >
        {title}
      </Text>
      {right ? <IconButton {...right} /> : <View style={styles.slot} />}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  slot: { width: 44, height: 44 },
  title: { flex: 1, textAlign: 'center' },
  small: { fontSize: 15, lineHeight: 19, letterSpacing: -0.15 },
});
