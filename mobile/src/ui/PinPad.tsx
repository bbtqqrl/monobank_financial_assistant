import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import Animated, {
  Easing,
  interpolateColor,
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  withTiming,
} from 'react-native-reanimated';

import { FONT } from '@/lib/fonts';
import { tap } from '@/lib/haptics';
import { PIN_LENGTH } from '@/lib/security';
import { useTheme, whiteAlpha, withAlpha } from '@/theme';
import { Icon, type IconName } from '@/ui/icons/Icon';
import { Text } from '@/ui/Text';

type Props = {
  title: string;
  // under the title; an error takes its place in red
  hint?: string;
  error?: string | null;
  // the code was right: the dots turn green before the pad goes away
  done?: boolean;
  disabled?: boolean;
  // false for a wrong code: the dots stay full in red for a beat, then fade
  onComplete: (code: string) => Promise<boolean> | boolean;
  // above the title: an avatar, a lock
  mark?: ReactNode;
  // the empty bottom-left key, e.g. Face ID
  extra?: { icon: IconName; label: string; onPress: () => void };
};

const KEY = 78;
const ROWS = [
  ['1', '2', '3'],
  ['4', '5', '6'],
  ['7', '8', '9'],
] as const;
const SPRING = { damping: 14, stiffness: 320 };
// the last dot shows filled for a moment before the result
const SETTLE_MS = 140;
// how long a wrong code stays on the dots in red
const WRONG_HOLD_MS = 420;
const TONE_MS = 160;

// A round glass key that sinks a little under the finger
function Key({ children, label, onPress, disabled, plain }: {
  children: ReactNode;
  label: string;
  onPress: () => void;
  disabled?: boolean;
  // no glass, for the side keys
  plain?: boolean;
}) {
  const { c, dark } = useTheme();
  const down = useSharedValue(0);
  // plain strings: the worklet below can't call withAlpha
  const rest = plain ? 'transparent' : withAlpha(c.white, whiteAlpha(0.5, dark));
  const held = plain ? 'transparent' : withAlpha(c.white, dark ? 0.2 : 0.95);
  const style = useAnimatedStyle(() => ({
    transform: [{ scale: 1 - down.get() * 0.08 }],
    backgroundColor: interpolateColor(down.get(), [0, 1], [rest, held]),
  }));

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={disabled}
      // on touch-down, like the phone's own passcode: quick typing never drops a digit
      onPressIn={() => {
        down.set(withTiming(1, { duration: 70 }));
        onPress();
      }}
      onPressOut={() => down.set(withSpring(0, SPRING))}
      style={disabled && styles.off}
    >
      <Animated.View
        style={[
          styles.key,
          !plain && {
            borderColor: withAlpha(c.white, whiteAlpha(0.82, dark)),
            boxShadow: `0 10px 24px -14px ${withAlpha(c.shadow, 0.5)}`,
          },
          style,
        ]}
      >
        {children}
      </Animated.View>
    </Pressable>
  );
}

type Tone = 'idle' | 'error' | 'done';

// One place of the code: fills in quietly from the middle
function Dot({ filled, tone }: { filled: boolean; tone: Tone }) {
  const { c } = useTheme();
  const fill = useSharedValue(filled ? 1 : 0);
  // a wrong code fades out slower, so the red is seen going
  const out = tone === 'error' ? 260 : 110;
  useEffect(() => {
    fill.set(withTiming(filled ? 1 : 0, { duration: filled ? 140 : out, easing: Easing.out(Easing.cubic) }));
  }, [filled, fill, out]);

  // the colour flows into red or green instead of switching
  const red = useSharedValue(tone === 'error' ? 1 : 0);
  const green = useSharedValue(tone === 'done' ? 1 : 0);
  useEffect(() => {
    red.set(withTiming(tone === 'error' ? 1 : 0, { duration: TONE_MS }));
    green.set(withTiming(tone === 'done' ? 1 : 0, { duration: TONE_MS }));
  }, [tone, red, green]);

  // plain strings: the worklet below can't call withAlpha
  const fills = [c.accent, c.danger, c.category.green];
  const glows = fills.map((f) => withAlpha(f, 0.7));
  const inner = useAnimatedStyle(() => {
    const mix = (v: string[]) =>
      interpolateColor(green.get(), [0, 1], [interpolateColor(red.get(), [0, 1], [v[0]!, v[1]!]), v[2]!]);
    return {
      transform: [{ scale: 0.5 + fill.get() * 0.5 }],
      opacity: fill.get(),
      backgroundColor: mix(fills),
      boxShadow: `0 0 12px ${mix(glows)}`,
    };
  });

  const ring = tone === 'error' ? c.danger : tone === 'done' ? c.category.green : withAlpha(c.ink, 0.28);
  return (
    <View style={[styles.dot, { borderColor: ring }]}>
      <Animated.View style={[styles.dotFill, inner]} />
    </View>
  );
}

// The app's own code pad, on the app's backdrop: a mark, the dots and round
// glass keys. Used on the lock screen and when setting the code.
export function PinPad({ title, hint, error, done = false, disabled = false, onComplete, mark, extra }: Props) {
  const { c } = useTheme();
  const [code, setCode] = useState('');
  // a wrong code held on the dots in red before they empty
  const [wrong, setWrong] = useState(false);
  // the error stays red until typing starts again
  const failed = !!error && (wrong || code.length === 0);

  // functional updates: quick taps between renders all count
  const press = (digit: string) => {
    tap();
    setCode((now) => (now.length >= PIN_LENGTH ? now : now + digit));
  };

  // a full code is being checked: nothing to erase
  const erase = () => {
    tap();
    setCode((now) => (now.length >= PIN_LENGTH ? now : now.slice(0, -1)));
  };

  const latest = useRef(onComplete);
  useEffect(() => {
    latest.current = onComplete;
  });
  useEffect(() => {
    if (code.length < PIN_LENGTH) return;
    let alive = true;
    let hold: ReturnType<typeof setTimeout> | undefined;
    const settle = setTimeout(async () => {
      const ok = await latest.current(code);
      if (!alive) return;
      if (ok) {
        setCode('');
        return;
      }
      setWrong(true);
      hold = setTimeout(() => {
        setWrong(false);
        setCode('');
      }, WRONG_HOLD_MS);
    }, SETTLE_MS);
    return () => {
      alive = false;
      clearTimeout(settle);
      clearTimeout(hold);
    };
  }, [code]);

  const tone: Tone = done ? 'done' : wrong || failed ? 'error' : 'idle';

  return (
    <View style={styles.pad}>
      <View style={styles.head}>
        {mark}
        <Text variant="screenTitle" style={styles.title}>
          {title}
        </Text>
        <Text variant="rowCaption" tone={failed ? 'danger' : 'faint'} style={styles.hint}>
          {(failed ? error : hint) ?? ' '}
        </Text>
      </View>

      <View style={styles.dots} accessibilityLabel={`Введено ${code.length} з ${PIN_LENGTH}`}>
        {Array.from({ length: PIN_LENGTH }, (_, i) => (
          <Dot key={i} filled={done || i < code.length} tone={tone} />
        ))}
      </View>

      <View style={styles.grid}>
        {ROWS.map((row) => (
          <View key={row[0]} style={styles.row}>
            {row.map((d) => (
              <Key key={d} label={d} onPress={() => press(d)} disabled={disabled}>
                <Text style={styles.digit}>{d}</Text>
              </Key>
            ))}
          </View>
        ))}
        <View style={styles.row}>
          {extra ? (
            <Key plain label={extra.label} onPress={extra.onPress} disabled={disabled}>
              <Icon name={extra.icon} size={32} color={c.accent} weight={1.7} />
            </Key>
          ) : (
            <View style={styles.key} />
          )}
          <Key label="0" onPress={() => press('0')} disabled={disabled}>
            <Text style={styles.digit}>0</Text>
          </Key>
          <Key plain label="Стерти" onPress={erase} disabled={disabled || !code}>
            <Icon name="backspace" size={28} color={c.inkSoft} weight={1.7} />
          </Key>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  pad: { alignItems: 'center', gap: 30 },
  head: { alignItems: 'center', gap: 8 },
  title: { fontSize: 22, lineHeight: 28, marginTop: 6 },
  hint: { fontSize: 13, textAlign: 'center' },
  dots: { flexDirection: 'row', gap: 20 },
  dot: { width: 16, height: 16, borderRadius: 8, borderWidth: 1.5, alignItems: 'center', justifyContent: 'center' },
  dotFill: { width: 16, height: 16, borderRadius: 8 },
  grid: { gap: 16 },
  row: { flexDirection: 'row', gap: 24 },
  key: {
    width: KEY,
    height: KEY,
    borderRadius: KEY / 2,
    borderWidth: 1,
    borderColor: 'transparent',
    alignItems: 'center',
    justifyContent: 'center',
  },
  digit: { fontFamily: FONT.display.medium, fontSize: 32, lineHeight: 38 },
  off: { opacity: 0.4 },
});
