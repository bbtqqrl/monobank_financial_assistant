import MaskedView from '@react-native-masked-view/masked-view';
import { useEffect, useState } from 'react';
import { StyleSheet, View, type StyleProp, type TextStyle } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import Svg, { Defs, LinearGradient, Rect, Stop } from 'react-native-svg';

import { useTheme } from '@/theme';
import { Text } from '@/ui/Text';

const BAND = 70;
const SWEEP_MS = 1500;

type Props = {
  children: string;
  style?: StyleProp<TextStyle>;
};

// A line that's still being worked on: a soft light passes over the words
// from left to right, again and again. Plain text with Reduce Motion.
export function ShimmerText({ children, style }: Props) {
  const { c } = useTheme();
  const reduceMotion = useReducedMotion();
  const [width, setWidth] = useState(0);
  const at = useSharedValue(0);

  useEffect(() => {
    if (reduceMotion || width === 0) return;
    at.set(0);
    at.set(withRepeat(withTiming(1, { duration: SWEEP_MS, easing: Easing.inOut(Easing.quad) }), -1));
  }, [reduceMotion, width, at]);

  const band = useAnimatedStyle(() => ({ transform: [{ translateX: -BAND + at.get() * (width + BAND) }] }));

  const text = (
    <Text variant="rowCaption" numberOfLines={1} style={style}>
      {children}
    </Text>
  );
  if (reduceMotion) {
    return (
      <Text variant="rowCaption" tone="faint" numberOfLines={1} style={style}>
        {children}
      </Text>
    );
  }

  return (
    <MaskedView maskElement={text} accessible accessibilityLabel={children}>
      {/* only sizes the mask, never seen */}
      <View style={styles.hidden} onLayout={(e) => setWidth(e.nativeEvent.layout.width)}>
        {text}
      </View>
      <View style={[StyleSheet.absoluteFill, { backgroundColor: c.faint }]} />
      <Animated.View style={[styles.band, band]}>
        <Svg width={BAND} height="100%">
          <Defs>
            <LinearGradient id="shine" x1="0" y1="0" x2="1" y2="0">
              <Stop offset="0" stopColor={c.ink} stopOpacity={0} />
              <Stop offset="0.5" stopColor={c.ink} stopOpacity={1} />
              <Stop offset="1" stopColor={c.ink} stopOpacity={0} />
            </LinearGradient>
          </Defs>
          <Rect width={BAND} height="100%" fill="url(#shine)" />
        </Svg>
      </Animated.View>
    </MaskedView>
  );
}

const styles = StyleSheet.create({
  hidden: { opacity: 0 },
  band: { position: 'absolute', top: 0, bottom: 0, left: 0, width: BAND },
});
