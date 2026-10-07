import { StyleSheet, useWindowDimensions, type StyleProp, type ViewStyle } from 'react-native';
import Animated, { useAnimatedStyle, type SharedValue } from 'react-native-reanimated';

import { Backdrop, type BackdropVariant } from '@/ui/Backdrop';

type Props = {
  variant: BackdropVariant;
  // the scroll view's contentOffset.y
  offset: SharedValue<number>;
  // to cancel the padding of whatever it's placed in
  style?: StyleProp<ViewStyle>;
};

// The native tab bar looks for the screen's scroll view only through each
// view's first child: with the backdrop in front of the ScrollView it finds
// nothing, so the bar doesn't minimise and the iOS 26 edge blur is missing.
// So the backdrop sits inside the scroll content and moves against the scroll.
export function ScrollBackdrop({ variant, offset, style }: Props) {
  const { width, height } = useWindowDimensions();
  const pinned = useAnimatedStyle(() => ({ transform: [{ translateY: offset.value }] }));

  return (
    <Animated.View pointerEvents="none" style={[styles.fill, { width, height }, style, pinned]}>
      <Backdrop variant={variant} />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  fill: { position: 'absolute', top: 0, left: 0 },
});
