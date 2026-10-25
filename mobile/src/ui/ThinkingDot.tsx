import { useEffect } from 'react';
import Animated, {
  Easing,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';

import { useTheme } from '@/theme';

const SIZE = 9;
const PULSE_MS = 1100;

// One small dot that gently swells and fades while the assistant works.
// Still with Reduce Motion.
export function ThinkingDot() {
  const { c } = useTheme();
  const reduceMotion = useReducedMotion();
  const pulse = useSharedValue(1);

  useEffect(() => {
    if (reduceMotion) return;
    const ease = { duration: PULSE_MS / 2, easing: Easing.inOut(Easing.sin) };
    pulse.set(withRepeat(withSequence(withTiming(0, ease), withTiming(1, ease)), -1));
  }, [reduceMotion, pulse]);

  const style = useAnimatedStyle(() => ({
    opacity: 0.45 + pulse.get() * 0.55,
    transform: [{ scale: 0.7 + pulse.get() * 0.3 }],
  }));

  return (
    <Animated.View style={[{ width: SIZE, height: SIZE, borderRadius: SIZE / 2, backgroundColor: c.ink }, style]} />
  );
}
