import { useEffect } from 'react';
import { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';

// The ring around a picked item fades in rather than popping on
export function useSelectRing(selected: boolean) {
  const shown = useSharedValue(selected ? 1 : 0);

  useEffect(() => {
    shown.set(withTiming(selected ? 1 : 0, { duration: 160 }));
  }, [selected, shown]);

  return useAnimatedStyle(() => ({ opacity: shown.get() }));
}
