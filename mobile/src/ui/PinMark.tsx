import { StyleSheet, View } from 'react-native';

import { useMe } from '@/api/auth';
import { FONT } from '@/lib/fonts';
import { useTheme, withAlpha } from '@/theme';
import { Icon } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

// Above the code pad: the account's letter, like the Profile avatar, in a
// soft accent glow, with a small lock on its corner
export function PinMark() {
  const { c } = useTheme();
  const me = useMe();
  const letter = me.data?.email[0]?.toUpperCase();

  return (
    <View style={styles.wrap}>
      <View
        pointerEvents="none"
        style={[
          styles.glow,
          { experimental_backgroundImage: `radial-gradient(closest-side, ${withAlpha(c.accent, 0.35)}, ${withAlpha(c.accent, 0)})` },
        ]}
      />
      <View style={[styles.avatar, { experimental_backgroundImage: `linear-gradient(150deg, ${c.cardA}, ${c.cardB})` }]}>
        {letter ? (
          <Text style={[styles.letter, { color: c.cream }]}>{letter}</Text>
        ) : (
          <Icon name="lock" size={26} color={c.cream} weight={1.8} />
        )}
      </View>
      <View style={[styles.badge, { backgroundColor: c.accent, borderColor: c.bg }]}>
        <Icon name="lock" size={12} color={c.cream} weight={2.4} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { width: 72, height: 72, alignItems: 'center', justifyContent: 'center' },
  glow: { position: 'absolute', width: 180, height: 180 },
  avatar: { width: 72, height: 72, borderRadius: 26, alignItems: 'center', justifyContent: 'center' },
  letter: { fontFamily: FONT.display.semiBold, fontSize: 28, lineHeight: 34 },
  badge: {
    position: 'absolute',
    right: -6,
    bottom: -6,
    width: 26,
    height: 26,
    borderRadius: 13,
    borderWidth: 2.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
