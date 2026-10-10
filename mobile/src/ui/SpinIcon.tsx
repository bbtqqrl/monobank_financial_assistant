import { useEffect } from 'react';
import Animated, {
  cancelAnimation,
  Easing,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

import { Icon } from '@/ui/icons/Icon';

type Props = {
  spinning: boolean;
  color: string;
  size?: number;
};

const TURN_MS = 900;

// The refresh icon. It turns while something loads and finishes the turn
// it's on when that's done instead of snapping back.
export function SpinIcon({ spinning, color, size = 16 }: Props) {
  const reduceMotion = useReducedMotion();
  const turn = useSharedValue(0);

  useEffect(() => {
    if (reduceMotion) return;
    if (spinning) {
      turn.set(0);
      turn.set(withRepeat(withTiming(1, { duration: TURN_MS, easing: Easing.linear }), -1));
    } else {
      const at = turn.get();
      cancelAnimation(turn);
      if (at > 0) turn.set(withTiming(1, { duration: (1 - at) * TURN_MS * 1.6, easing: Easing.out(Easing.quad) }));
    }
  }, [spinning, reduceMotion, turn]);

  const style = useAnimatedStyle(() => ({ transform: [{ rotate: `${turn.get() * 360}deg` }] }));

  return (
    <Animated.View style={style}>
      <Icon name="refresh" size={size} color={color} weight={1.8} />
    </Animated.View>
  );
}
