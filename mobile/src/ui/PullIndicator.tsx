import {
  Platform,
  RefreshControl,
  StyleSheet,
  useWindowDimensions,
  type RefreshControlProps,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import Animated, {
  Extrapolation,
  interpolate,
  useAnimatedStyle,
  useDerivedValue,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated';

import { PULL_AT, type PullRefresh } from '@/lib/usePullRefresh';
import { useTheme } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Icon } from '@/ui/icons/Icon';

type Props = {
  // the scroll view's contentOffset.y
  offset: SharedValue<number>;
  // contentOffset.y when nothing is pulled
  rest: number;
  // where it sits on screen, from the top
  top: number;
  // to cancel the padding of whatever it's placed in
  style?: StyleProp<ViewStyle>;
};

const SIZE = 34;
const ICON = 17;

// Pull-to-refresh mark, shown only during the pull: it fades in and turns with
// it, and takes the accent once letting go will refresh. The refresh itself
// shows in the screen header. Pinned under the status bar against the scroll,
// over the backdrop (see ScrollBackdrop).
export function PullIndicator({ offset, rest, top, style }: Props) {
  const { c } = useTheme();
  const { width } = useWindowDimensions();
  const ready = useDerivedValue(() => withTiming(rest - offset.get() >= PULL_AT ? 1 : 0, { duration: 120 }));

  const pinned = useAnimatedStyle(() => ({
    opacity: interpolate(rest - offset.get(), [12, 56], [0, 1], Extrapolation.CLAMP),
    transform: [{ translateY: offset.get() + top }],
  }));
  const turned = useAnimatedStyle(() => ({
    transform: [{ rotate: `${Math.min(Math.max(0, rest - offset.get()) / PULL_AT, 1) * 300}deg` }],
  }));
  const plain = useAnimatedStyle(() => ({ opacity: 1 - ready.get() }));
  const accent = useAnimatedStyle(() => ({ opacity: ready.get() }));

  // Android has RefreshControl's own spinner
  if (Platform.OS !== 'ios') return null;

  return (
    <Animated.View pointerEvents="none" style={[styles.box, { width }, style, pinned]}>
      <Glass radius={SIZE / 2} style={styles.glass} contentStyle={styles.center}>
        <Animated.View style={turned}>
          <Animated.View style={plain}>
            <Icon name="refresh" size={ICON} color={c.inkSoft} weight={1.8} />
          </Animated.View>
          <Animated.View style={[StyleSheet.absoluteFill, accent]}>
            <Icon name="refresh" size={ICON} color={c.accent} weight={1.8} />
          </Animated.View>
        </Animated.View>
      </Glass>
    </Animated.View>
  );
}

type ControlProps = Omit<RefreshControlProps, 'refreshing' | 'onRefresh'> & { pull: PullRefresh };

// Android's own control, spinning while the refresh runs. It reads the status
// itself so the screen doesn't re-render for it.
export function PullRefreshControl({ pull, ...props }: ControlProps) {
  const refreshing = pull.status.useValue() === 'busy';
  return <RefreshControl {...props} refreshing={refreshing} onRefresh={pull.start} />;
}

const styles = StyleSheet.create({
  box: { position: 'absolute', top: 0, left: 0, alignItems: 'center' },
  glass: { width: SIZE, height: SIZE },
  center: { alignItems: 'center', justifyContent: 'center' },
});
