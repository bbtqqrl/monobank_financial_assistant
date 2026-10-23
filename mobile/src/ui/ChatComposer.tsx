import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, TextInput, View } from 'react-native';
import Animated, {
  Easing,
  FadeIn,
  FadeOut,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';

import { FONT } from '@/lib/fonts';
import { tap, toggle } from '@/lib/haptics';
import { useTheme } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Icon } from '@/ui/icons/Icon';

// the backend takes up to this many characters
const MAX_LENGTH = 4000;
const MAX_LINES_HEIGHT = 120;
const SWAP_IN = FadeIn.duration(160);
const SWAP_OUT = FadeOut.duration(120);
const SHOW_MS = 180;

type Props = {
  // a reply is on its way: the button stops it instead of sending
  busy: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
  // whether there's something typed, so the screen can tuck the chips away
  onTyping?: (typing: boolean) => void;
};

// The question field over the tab bar: grows with the text up to a few lines.
// The round button comes up once there's something to send, and while an
// answer is coming it stops it.
export function ChatComposer({ busy, onSend, onStop, onTyping }: Props) {
  const { c } = useTheme();
  const [text, setText] = useState('');
  const ready = text.trim().length > 0;
  const active = busy || ready;
  const shown = useSharedValue(active ? 1 : 0);

  useEffect(() => {
    shown.set(withTiming(active ? 1 : 0, { duration: SHOW_MS, easing: Easing.out(Easing.cubic) }));
  }, [active, shown]);

  const appear = useAnimatedStyle(() => ({
    opacity: shown.get(),
    transform: [{ scale: 0.6 + shown.get() * 0.4 }],
  }));

  const change = (next: string) => {
    if (!!next.trim() !== ready) onTyping?.(!!next.trim());
    setText(next);
  };

  const press = () => {
    if (busy) {
      toggle();
      onStop();
      return;
    }
    if (!ready) return;
    tap();
    onSend(text);
    change('');
  };

  return (
    <Glass radius={24} contentStyle={styles.row}>
      <TextInput
        value={text}
        onChangeText={change}
        placeholder="Спитай про свої гроші"
        placeholderTextColor={c.ghost}
        multiline
        maxLength={MAX_LENGTH}
        style={[styles.input, { color: c.ink }]}
        selectionColor={c.accent}
        accessibilityLabel="Питання асистенту"
      />
      {/* keeps its place when hidden, so the text doesn't reflow as it comes and goes */}
      <Animated.View style={appear} pointerEvents={active ? 'auto' : 'none'}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={busy ? 'Зупинити' : 'Надіслати'}
          accessibilityElementsHidden={!active}
          importantForAccessibility={active ? 'auto' : 'no-hide-descendants'}
          hitSlop={8}
          onPress={press}
          style={[styles.button, { backgroundColor: c.accentFill }]}
        >
          {busy ? (
            <Animated.View key="stop" entering={SWAP_IN} exiting={SWAP_OUT}>
              <View style={[styles.stop, { backgroundColor: c.onPrimary }]} />
            </Animated.View>
          ) : (
            <Animated.View key="send" entering={SWAP_IN} exiting={SWAP_OUT}>
              <Icon name="arrowUp" size={18} weight={2.2} color={c.onPrimary} />
            </Animated.View>
          )}
        </Pressable>
      </Animated.View>
    </Glass>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'flex-end', paddingLeft: 16, paddingRight: 6, paddingVertical: 6, gap: 8 },
  input: {
    flex: 1,
    maxHeight: MAX_LINES_HEIGHT,
    fontFamily: FONT.ui.medium,
    fontSize: 15,
    lineHeight: 20,
    paddingTop: 8,
    paddingBottom: 8,
  },
  button: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  stop: { width: 11, height: 11, borderRadius: 3 },
});
