import { useEffect, useRef, useState } from 'react';
import { AppState, Pressable, StyleSheet, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { FullWindowOverlay } from 'react-native-screens';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { signOut } from '@/api/auth';
import { failure, settle, warning } from '@/lib/haptics';
import {
  authenticate,
  authenticating,
  biometricEnabled,
  checkPin,
  LOCK_DELAY_MS,
  lockAfter,
  lockEnabled,
  locked,
  pinRest,
  useBiometry,
} from '@/lib/security';
import { useTheme, withAlpha } from '@/theme';
import { PinBackdrop } from '@/ui/PinBackdrop';
import { Glass } from '@/ui/Glass';
import { Icon } from '@/ui/icons/Icon';
import { PinMark } from '@/ui/PinMark';
import { PinPad } from '@/ui/PinPad';
import { Text } from '@/ui/Text';

const FADE_MS = 200;

// the dots turn green for a beat, then the lock goes
const OPEN_DELAY_MS = 260;

// seconds left of the rest after too many wrong codes, ticking down.
// Counted from the rest's own start until the first tick, so a lock screen
// that has been up for a while doesn't show a longer wait for a second.
function useRestLeft() {
  const { from, until } = pinRest.useValue();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (until <= Date.now()) return;
    const t = setInterval(() => {
      const next = Date.now();
      setNow(next);
      if (next >= until) clearInterval(t);
    }, 1000);
    return () => clearInterval(t);
  }, [until]);
  return Math.max(0, Math.ceil((until - Math.max(now, from)) / 1000));
}

// The app's code, or Face ID when it's on: asks on its own when it appears
// and when the app comes back from the background
function LockScreen() {
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  const biometry = useBiometry();
  const useFace = biometricEnabled.useValue() && !!biometry?.available;
  const [done, setDone] = useState(false);
  const rest = useRestLeft();

  const open = () => {
    settle();
    setDone(true);
    setTimeout(() => locked.set(false), OPEN_DELAY_MS);
  };

  useEffect(() => {
    if (!useFace) return;
    const tryFace = async () => {
      if (await authenticate('Розблокувати blink')) {
        settle();
        locked.set(false);
      }
    };
    if (AppState.currentState === 'active') tryFace();
    let last = AppState.currentState;
    // from the background only: a cancelled prompt also ends in "active"
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active' && last === 'background') tryFace();
      last = state;
    });
    return () => sub.remove();
  }, [useFace]);

  const enter = async (code: string) => {
    const result = await checkPin(code);
    if (result === 'ok') {
      open();
      return true;
    }
    failure();
    return false;
  };

  // a forgotten code: out of the account, the code goes with it (see clearPin)
  const forgot = () => {
    warning();
    signOut();
  };

  return (
    <View style={[styles.screen, { paddingTop: insets.top + 40, paddingBottom: Math.max(insets.bottom, 16) + 8 }]}>
      <PinBackdrop />
      <View style={styles.middle}>
        <PinPad
          mark={<PinMark />}
          done={done}
          hint={rest ? `Забагато спроб, зачекай ${rest} с` : undefined}
          disabled={rest > 0}
          onComplete={enter}
          extra={
            useFace
              ? {
                  icon: 'faceid',
                  label: biometry?.name ?? 'Face ID',
                  onPress: async () => {
                    if (await authenticate('Розблокувати blink')) open();
                  },
                }
              : undefined
          }
        />
      </View>
      <Pressable accessibilityRole="button" hitSlop={8} onPress={forgot} style={({ pressed }) => pressed && styles.pressed}>
        <Text variant="link" style={[styles.forgot, { color: withAlpha(c.ink, 0.6) }]}>
          Забув код? Вийти з акаунта
        </Text>
      </Pressable>
    </View>
  );
}

// in the app switcher, instead of balances
function Cover() {
  const { c } = useTheme();
  return (
    <View style={styles.screen}>
      <PinBackdrop />
      <View style={styles.middle}>
        <Glass radius={30} style={styles.mark} contentStyle={styles.markInner}>
          <Icon name="lock" size={30} color={c.inkSoft} weight={1.8} />
        </Glass>
      </View>
    </View>
  );
}

// Lock screen and app switcher cover, in a window above everything, sheets included.
// Rendered only while signed in.
export function AppLock() {
  const isLocked = locked.useValue();
  const enabled = lockEnabled.useValue();
  const [away, setAway] = useState(false);
  const leftAt = useRef<number | null>(null);

  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') {
        const left = leftAt.current;
        leftAt.current = null;
        if (lockEnabled.get() && left !== null && Date.now() - left >= LOCK_DELAY_MS[lockAfter.get()]) {
          locked.set(true);
        }
        setAway(false);
        return;
      }
      // a Face ID prompt makes the app inactive too; leaving for real still counts
      if (state === 'inactive' && authenticating.get()) return;
      if (state === 'background') {
        leftAt.current ??= Date.now();
        // locks right away, so even the app switcher's snapshot is the lock screen
        if (lockEnabled.get() && lockAfter.get() === 'now') locked.set(true);
      }
      setAway(true);
    });
    return () => sub.remove();
  }, []);

  const covered = away && enabled && !isLocked;
  if (!isLocked && !covered) return null;

  return (
    <FullWindowOverlay>
      <Animated.View
        key={isLocked ? 'lock' : 'cover'}
        entering={isLocked ? undefined : FadeIn.duration(FADE_MS)}
        style={StyleSheet.absoluteFill}
      >
        {isLocked ? <LockScreen /> : <Cover />}
      </Animated.View>
    </FullWindowOverlay>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, paddingHorizontal: 20 },
  middle: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  mark: { width: 84, height: 84 },
  markInner: { alignItems: 'center', justifyContent: 'center' },
  forgot: { textAlign: 'center', fontSize: 14 },
  pressed: { opacity: 0.6 },
});
