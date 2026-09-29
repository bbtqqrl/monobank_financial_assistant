import { Pressable, StyleSheet, View } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';

import { useTheme, withAlpha } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Icon, type IconName } from '@/ui/icons/Icon';

export type IconButtonProps = {
  icon: IconName;
  // read by VoiceOver, the button has no visible text
  label: string;
  onPress?: () => void;
  // unread marker in the corner
  dot?: boolean;
  weight?: number;
};

const SIZE = 44;

export function IconButton({ icon, label, onPress, dot = false, weight }: IconButtonProps) {
  const { c } = useTheme();
  const pressed = useSharedValue(0);
  const style = useAnimatedStyle(() => ({ transform: [{ scale: 1 - pressed.value * 0.08 }] }));

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      hitSlop={6}
      onPress={onPress}
      onPressIn={() => pressed.set(withTiming(1, { duration: 90 }))}
      onPressOut={() => pressed.set(withTiming(0, { duration: 180 }))}
    >
      <Animated.View style={style}>
        <Glass radius={15} style={styles.size} contentStyle={styles.center}>
          <Icon name={icon} size={20} weight={weight} />
          {dot ? (
            <View style={[styles.dot, { backgroundColor: c.accent, borderColor: withAlpha(c.white, 0.9) }]} />
          ) : null}
        </Glass>
      </Animated.View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  size: { width: SIZE, height: SIZE },
  center: { alignItems: 'center', justifyContent: 'center' },
  // Figma puts it at 25,11 of the button, the glass border takes 1pt
  dot: { position: 'absolute', left: 24, top: 10, width: 7, height: 7, borderRadius: 4, borderWidth: 1.5 },
});
